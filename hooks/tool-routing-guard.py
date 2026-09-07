#!/usr/bin/env python3
"""tool-routing-guard (PreToolUse / WebFetch|WebSearch): nudges toward the
registered retrieval MCPs (context7, firecrawl, tavily) at the moment the model
reaches for a built-in web tool instead.

Fourth hook in the family:
  1. autoload-judgment.py        (SessionStart)
  2. fleet-delegation-guard.py   (PreToolUse / Bash)
  3. skill-routing-guard.py      (UserPromptSubmit)
  4. tool-routing-guard.py       (PreToolUse / WebFetch|WebSearch)
  5. retrieval-honesty-guard.py  (Stop)

WHY THIS LAYER EXISTS (2026-08-27 tool-usage audit over 50+ sessions):
Context7 was essentially unused despite being installed; sessions cited
"Docs (context7, psycopg3 API reference)" with NO matching tool call in the
transcript. Firecrawl had one genuine multi-source use while sessions did
page-by-page WebFetch where firecrawl_map/crawl fit better. Tavily was
near-absent. The prompt-level guards cannot catch any of this,
because the failure happens MID-SESSION at tool-choice time, long after the
user's prompt was submitted. Only a PreToolUse hook on the built-in web tools
sees that moment.

DESIGN — once per session per nudge class, then silent:
Unlike the Bash delegation guard (whose deploy shapes are rare per session),
WebFetch/WebSearch can fire dozens of times in a research session, so an
every-call reminder would be the wolf-crying failure the routing guards'
doctrine names. Each nudge class therefore fires ONCE per session, tracked by
marker files under STATE_DIR keyed on session_id (override the dir with
CLAUDE_TOOL_ROUTING_STATE_DIR for the self-test). Three classes:

  a. websearch-alternatives -- any WebSearch call: tavily_search /
     firecrawl_search are registered user-scope and return structured results
     with raw content; the built-in is fine for a quick lookup, but a research
     session should know the better tools exist.
  b. docs-url-context7 -- a WebFetch whose URL is docs-shaped (docs.*,
     /docs/, readthedocs, MDN, learn.microsoft, /reference/ ...): context7
     serves current, version-pinned library docs without page-by-page fetching.
  c. page-by-page-firecrawl -- the 3rd+ WebFetch this guard has
     itself observed this session (own state dir, NOT transcript parsing): the audit's exact finding; firecrawl_map/crawl
     or tavily_extract cover a site in one call instead of N.

ERROR CONTRACT: silent on any internal error, exit 0 -- same choice as the
routing guards (3+4), NOT the loud-on-parse-failure choice of the delegation
guard. Rationale: this hook is a frequency-limited nudge, and its worst
failure mode is crying wolf on every fetch of a long session; a missed nudge
costs one reminder. The delegation guard made the opposite choice because a
silently-dead deploy gate is dangerous; a silently-dead nudge is not.

Never blocks, never sets decision/permissionDecision -- reminder-only, same
non-blocking contract as the whole family. Subagents get the same nudges (a
research subagent can load the MCP tools via ToolSearch), so there is no
agent_id asymmetry here.
"""
import hashlib
import json
import os
import re
import sys

STATE_DIR = os.environ.get(
    "CLAUDE_TOOL_ROUTING_STATE_DIR", "/tmp/claude-tool-routing-guard"
)

# 2026-08-27 owner directive ("actually works 90%+ where there's a use case"):
# the docs-URL lane is ENFORCED, not just reminded. A reminder cannot promise a
# compliance rate; a deny can. Contract: the FIRST docs-shaped WebFetch of a
# session is DENIED with rerouting instructions and the marker is written, so
# any retry (e.g. after context7 turned out not to cover the page) PASSES
# automatically -- worst case is one denied call per session, never a dead end.
# This is a deliberate, narrow departure from the hook family's never-block
# contract, applied ONLY where the correct alternative is near-deterministic
# (library docs -> context7). WebSearch and page-by-page stay remind-only:
# forcing those would misfire on legitimate quick lookups.
# Kill-switch: CLAUDE_TOOL_ROUTING_ENFORCE=0 downgrades the deny to a reminder.
ENFORCE = os.environ.get("CLAUDE_TOOL_ROUTING_ENFORCE", "1") != "0"

MSG_DOCS_DENY = (
    "tool-routing-guard DENIED this WebFetch (docs-shaped URL, first one this "
    "session). Query context7 FIRST for library/API docs: ToolSearch "
    "'select:mcp__context7__resolve-library-id,mcp__context7__query-docs', then "
    "resolve-library-id -> query-docs. If context7 does not cover this page, "
    "simply RE-ISSUE the same WebFetch -- it will pass now (the gate arms only "
    "once per session). 2026-08-27 measured baseline: 2 context7 calls vs ~1,083 "
    "built-in web calls in 30 days; this gate exists to close that gap."
)

DOCS_URL = re.compile(
    r"(?:^|//|\.)docs\.[a-z]"          # docs.python.org, docs.sqlalchemy.org
    r"|/docs?/"                         # example.com/docs/..., /doc/
    r"|/documentation\b"
    r"|readthedocs\."
    r"|developer\.mozilla\.org"
    r"|learn\.microsoft\.com"
    r"|/(?:api-)?reference\b",
    re.I,
)

MSG_WEBSEARCH = (
    "tool-routing-guard: WebSearch call detected (once-per-session reminder). "
    "tavily and firecrawl MCP servers are registered user-scope and connected: "
    "mcp__tavily__tavily_search returns structured results with raw page content "
    "(skips the search->fetch round trip), and mcp__firecrawl__firecrawl_search "
    "does the same with scraping built in. Load via ToolSearch "
    "('select:mcp__tavily__tavily_search' or 'select:mcp__firecrawl__firecrawl_search') "
    "when the session needs more than one quick lookup. A single lookup via the "
    "built-in is fine -- proceed if that is all this is."
)

MSG_DOCS_URL = (
    "tool-routing-guard: this WebFetch targets a documentation URL "
    "(once-per-session reminder). context7 MCP is registered user-scope and "
    "connected -- mcp__context7__resolve-library-id then mcp__context7__query-docs "
    "serves current, version-aware library/API docs in one call, usually better "
    "than fetching doc pages one by one (2026-08-27 audit: sessions cited library "
    "docs with no context7 call in the transcript). Load via ToolSearch "
    "('select:mcp__context7__resolve-library-id,mcp__context7__query-docs')."
)

MSG_PAGE_BY_PAGE = (
    "tool-routing-guard: this session has already made 2+ WebFetch calls "
    "(once-per-session reminder). Page-by-page fetching is the exact pattern the "
    "2026-08-27 tool-usage audit flagged. Multi-page options, in order:\n"
    "  - FREE / robots-compliant: the agent-reach skill's bounded crawl "
    "(`agent-reach web crawl`); web extract --schema "
    "for deterministic fields, web diagnose for static-vs-JS. Its doctor --json "
    "precheck is MANDATORY, and disclose that its only active web backend is Jina "
    "Reader -- a REMOTE reader, so the target redirects/origin are not locally "
    "verified. That remote-reader boundary is why this is the multi-page option, "
    "NOT a default for single-page reads.\n"
    "  - CREDIT-METERED: mcp__firecrawl__firecrawl_map enumerates a site URL list "
    "in one call, mcp__firecrawl__firecrawl_crawl collects many pages in one call, "
    "and mcp__tavily__tavily_extract batch-extracts a URL list. Registered "
    "user-scope and connected; load via ToolSearch. Prefer these for JS-heavy or "
    "blocked targets.\n"
    "If these fetches are genuinely unrelated one-off pages, proceed as is."
)


def _session_key(payload: dict) -> str:
    sid = payload.get("session_id")
    if isinstance(sid, str) and sid:
        return sid
    tp = payload.get("transcript_path")
    if isinstance(tp, str) and tp:
        return hashlib.sha1(tp.encode()).hexdigest()[:16]
    return "unknown-session"


def _fired_before(key: str, nudge_id: str) -> bool:
    """True if this nudge class already fired this session; records the firing
    otherwise. Any filesystem error reads as 'already fired' -- fail toward
    silence, per this hook's error contract."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        marker = os.path.join(STATE_DIR, f"{key}.{nudge_id}")
        if os.path.exists(marker):
            return True
        with open(marker, "w"):
            pass
        return False
    except Exception:
        return True


def _bump_and_count(key: str) -> int:
    """Increment this session's web-call counter and return the new total.

    2026-08-27: REPLACES a transcript-parsing counter that read
    payload["transcript_path"]. That key's presence in a PreToolUse payload was
    never verified -- and if absent, the old counter returned 0 forever and the
    page-by-page class silently never fired. A nudge that can never fire is
    precisely the "installed but never invoked" failure this hook exists to fix,
    so the dependency is removed rather than assumed: the hook now counts only
    what it has itself observed, which is also the more honest semantics
    ("web calls seen since this guard went live"). Any filesystem error returns
    0, suppressing the nudge -- fail toward silence, per the error contract.
    """
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        counter = os.path.join(STATE_DIR, f"{key}.webcalls")
        n = 0
        if os.path.exists(counter):
            with open(counter) as f:
                n = int(f.read().strip() or "0")
        n += 1
        with open(counter, "w") as f:
            f.write(str(n))
        return n
    except Exception:
        return 0


def collect_nudges(payload: dict, key: str) -> list:
    """Return the list of (nudge_id, message) applicable to this call, BEFORE
    the once-per-session filter. Importable so the self-test can reason about
    which class matched independently of marker state."""
    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    nudges = []
    if tool == "WebSearch":
        nudges.append(("websearch-alternatives", MSG_WEBSEARCH))
    elif tool == "WebFetch":
        url = tool_input.get("url") if isinstance(tool_input, dict) else ""
        if isinstance(url, str) and DOCS_URL.search(url):
            nudges.append(("docs-url-context7", MSG_DOCS_URL))
        if _bump_and_count(key) >= 3:
            nudges.append(("page-by-page-firecrawl", MSG_PAGE_BY_PAGE))
    return nudges


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return
        key = _session_key(payload)
        nudges = collect_nudges(payload, key)
        if not nudges:
            return
        fresh = []
        for nid, msg in nudges:
            if _fired_before(key, nid):
                continue
            if nid == "docs-url-context7" and ENFORCE:
                # Enforced lane: deny with rerouting instructions. The marker was
                # just written by _fired_before, so the model's retry passes.
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": MSG_DOCS_DENY,
                    }
                }))
                return
            fresh.append(msg)
        if not fresh:
            return
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "\n\n---\n\n".join(fresh),
            }
        }))
    except Exception:
        # Silent on any internal error, per the error contract in the docstring.
        return


if __name__ == "__main__":
    main()

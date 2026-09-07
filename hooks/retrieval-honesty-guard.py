#!/usr/bin/env python3
"""Stop-hook guard: block a turn that asserts unverifiability without retrieving.

Failure mode this exists for (2026-09-07): the assistant emitted "past my cutoff,
can't verify" about a real, checkable fact while holding tavily, firecrawl,
agent-reach and a researcher agent. The tell is not the topic -- it is the
sentence. So this fires on the sentence, and clears only if a retrieval tool
actually ran in the same turn.

Fails OPEN on every error: a guard that crashes must never wedge a session.
"""
import json, sys, re, hashlib, pathlib, tempfile, os

TELLS = [
    r"past my (?:knowledge[- ])?cut[- ]?off",
    r"beyond my (?:knowledge[- ])?cut[- ]?off",
    r"after my (?:knowledge[- ])?cut[- ]?off",
    r"my (?:knowledge[- ])?cut[- ]?off (?:is|was|means)",
    r"\bI (?:can'?t|cannot|am unable to|won'?t be able to) (?:verify|confirm|check|validate)",
    r"\bI have no way to (?:verify|confirm|check|know)",
    r"\bI'?m not able to (?:verify|confirm|check)",
    r"\bI don'?t (?:know|have any way of knowing) (?:whether|if) .{0,80}?(?:exists?|is real|is right|shipped|released)",
    r"as of my (?:last )?(?:training|update|knowledge)",
    r"\bI can'?t (?:look (?:this|that|it) up|search|browse)",
    r"without (?:access to )?(?:the )?(?:internet|live (?:data|web)|web access)",
]
TELL_RE = re.compile("|".join(TELLS), re.I)

# Any of these running in the turn means retrieval was actually attempted.
RETRIEVAL_TOOL_RE = re.compile(
    r"(tavily|firecrawl|context7|WebSearch|WebFetch|agent[-_]reach|exa|perplexity|brave)", re.I
)
# A dispatched subagent (researcher/Explore/general-purpose) also counts.
AGENT_TOOLS = {"Agent", "Task", "SendMessage"}
# Bash/Skill payloads that invoke a retrieval CLI.
PAYLOAD_RE = re.compile(r"(agent[-_]reach|tavily|firecrawl|curl\s+https?://)", re.I)


def blocks(msg):
    c = msg.get("content")
    return c if isinstance(c, list) else []


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}

    # Never loop: the harness sets this when we already blocked once.
    if payload.get("stop_hook_active"):
        return 0

    tpath = payload.get("transcript_path")
    if not tpath or not pathlib.Path(tpath).exists():
        return 0

    entries = []
    with open(tpath, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    # Walk back to the start of the current turn: the last REAL user message
    # (one carrying human text, not a tool_result envelope).
    start = 0
    for i in range(len(entries) - 1, -1, -1):
        e = entries[i]
        if e.get("type") != "user":
            continue
        msg = e.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            start = i
            break
        if isinstance(content, list) and any(
            b.get("type") == "text" and b.get("text", "").strip() for b in content
        ):
            start = i
            break

    turn = entries[start:]

    used_retrieval = False
    final_text = []
    for e in turn:
        if e.get("type") != "assistant":
            continue
        for b in blocks(e.get("message") or {}):
            btype = b.get("type")
            if btype == "text":
                final_text.append(b.get("text", ""))
            elif btype == "tool_use":
                name = b.get("name", "") or ""
                if RETRIEVAL_TOOL_RE.search(name) or name in AGENT_TOOLS:
                    used_retrieval = True
                else:
                    try:
                        if PAYLOAD_RE.search(json.dumps(b.get("input") or {})):
                            used_retrieval = True
                    except Exception:
                        pass

    if used_retrieval:
        return 0

    text = "\n".join(final_text)
    m = TELL_RE.search(text)
    if not m:
        return 0

    # Fire at most once per (session, response) so a re-run can't ping-pong.
    sid = str(payload.get("session_id") or "nosession")
    stamp = hashlib.sha256((sid + text).encode()).hexdigest()[:16]
    marker = pathlib.Path(tempfile.gettempdir()) / f"claude-retrieval-guard-{stamp}"
    if marker.exists():
        return 0
    try:
        marker.touch()
    except Exception:
        pass

    quoted = m.group(0).strip()
    print(json.dumps({
        "decision": "block",
        "reason": (
            f'You wrote "{quoted}" but called no retrieval tool this turn. '
            "That is the motivated-non-retrieval failure mode: asserting a gap "
            "instead of closing one you have the tools to close.\n\n"
            "Before you finish: run the retrieval ladder for this claim -- "
            "context7 for library/API behaviour; tavily_search or firecrawl_search "
            "for anything post-cutoff, any product/model/version/pricing claim, or "
            "any 'is X real / is X better' question; agent-reach or firecrawl "
            "map/crawl for multi-page reads; the researcher agent when it needs "
            "several sources cross-checked. Prefer first-party pages over "
            "aggregators, and treat vendor claims about competitors as vendor claims.\n\n"
            "Then rewrite the answer with what you actually found. If retrieval "
            "genuinely fails, say what you searched, what came back, and why it "
            "was insufficient -- an unverifiability claim is only honest once "
            "you have tried."
        ),
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)   # fail open, always

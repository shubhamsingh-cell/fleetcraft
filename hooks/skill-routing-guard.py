#!/usr/bin/env python3
"""skill-routing-guard (UserPromptSubmit): reminds which locally-ported skill to
prefer for tabular-file, office-document, and pre-share-preflight work, so the
newly-ported skills (duckdb, qsv, markitdown, presidio, gitleaks) actually get
auto-invoked instead of the model defaulting to ad-hoc pandas scripts or
skipping a PII/secret preflight before something leaves the machine.

Third hook in this repo's family, alongside:
  1. autoload-judgment.py       (SessionStart)
  2. fleet-delegation-guard.py  (PreToolUse / Bash)
  3. skill-routing-guard.py     (UserPromptSubmit, this file)

Same non-blocking contract as the other two: on a category match, print a JSON
hookSpecificOutput.additionalContext block; on no match, or any internal
error, stay completely silent and exit 0. This hook NEVER sets
`continue`/`decision` to block -- it only injects a reminder, same as the
other two. (This particular file also generalizes to a fourth category, a
UserPromptSubmit-based routing reminder for external-service-shaped asks
rather than skill routing -- see hooks/README.md for that pattern; it isn't
included as a standalone hook in this repo since its category list is
deployment-specific.)

=============================================================================
CRITICAL DESIGN DIFFERENCE from service-routing-guard
=============================================================================
service-routing-guard vetoes globally on any HARD_CODE_CTX signal (file
extensions, src/ paths, snake_case identifiers, call syntax, code nouns like
module/function/config). This hook must NOT copy that veto. The skills routed
here exist specifically to act ON code/data-shaped prompts -- a local CSV
path, a .docx attachment, a staged diff -- so a global "this looks like code"
veto would suppress every true positive this hook exists to catch.

Precision instead comes from requiring an UNAMBIGUOUS FILE-TYPE OBJECT in the
prompt, not from vetoing code-shaped language. Exactly three categories, each
gated on BOTH an intent verb AND an object match:

  a. tabular-analysis -- intent (analyze/profile/summarize/stats/query/
     aggregate/join/dedupe/count rows/explore) + a standalone token ending
     .csv/.tsv/.parquet (or the words "parquet file(s)"). Routes to duckdb +
     qsv.
  b. doc-extract -- intent (read/extract/convert/summarize/pull text/"what
     does ... say") + a standalone token ending .docx/.doc/.pptx/.epub/.eml/
     .msg/.odt/.rtf. Deliberately EXCLUDES .pdf and .xlsx/.xlsm/.csv -- those
     have their own dedicated pdf/xlsx skills and must never be double-routed
     here. Routes to markitdown.
  c. share-preflight -- intent (share/send/export/upload/hand over/post) +
     EITHER an external-audience phrase (externally / with the client / with
     the team / publicly / outside) OR an explicit sensitive-data token
     (PII / redact / sanitize / scrub / anonymize). No file-extension gate by
     design -- a share/export ask is the trigger regardless of file type.
     Routes to presidio + gitleaks.

For (a)/(b) the object match must be a standalone file-reference token (a
path/filename shape immediately before the extension, not a bare word like
"csv" with no dot), and a cheap fenced-code / path-heavy suppress
(CODE_ADJACENT: a ``` fence, src/, def , import , from X import, class X(,
function() ) vetoes a match even when the extension token is present -- a
prompt that is really about existing code that happens to touch a data file
should not fire. (c) has no file-extension gate and therefore no
CODE_ADJACENT suppress -- see the category definition above.

DEFAULT TO SILENCE, same governing principle as service-routing-guard: a
missed reminder is cheap, a wolf-crying hook gets ignored. Ordinary code
discussion ("fix the csv parser in ingest.py", "why does the export endpoint
500", "read config.json and summarize the schema") must produce zero
injection. See selftest-guards.py's skill-routing section for the enforced
positive/negative corpora.
"""
import json
import re
import sys

# ---------------------------------------------------------------------------
# Shared suppress: fenced code / path-heavy signals immediately adjacent to
# what would otherwise read as a file-object match. Cheap on purpose -- this
# is not trying to be a full code detector (that's the veto this hook exists
# to NOT copy), just a narrow guard against "this prompt is actually about
# source code that happens to mention a data/doc file".
# ---------------------------------------------------------------------------
CODE_ADJACENT = re.compile(
    r"```"
    r"|\bsrc/"
    r"|\bdef\s"
    r"|\bimport\s"
    r"|\bfrom\s+\S+\s+import\b"
    r"|\bclass\s+\w+[:(]"
    r"|\bfunction\s*\(",
    re.I,
)

# ---------------------------------------------------------------------------
# Categories. `intent` = gate 1 (action verb). `requires` = gate 2 (the
# unambiguous object -- a file-extension token for (a)/(b), an audience
# phrase or sensitive-data token for (c)). `suppress` = code-adjacency veto,
# only wired for (a)/(b) per the design note above.
# ---------------------------------------------------------------------------
CATEGORIES = [
    dict(
        id="tabular-analysis",
        intent=re.compile(
            r"\b(?:analyz(?:e|es|ing)|profil(?:e|es|ing)|summariz(?:e|es|ing)|stats?"
            r"|quer(?:y|ies|ying)|aggregat(?:e|es|ing)|join(?:ing)?"
            r"|dedup(?:e|es|ing|licate|licates|licating)|explor(?:e|es|ing))\b"
            r"|\bcount(?:ing)?\s+rows?\b",
            re.I,
        ),
        requires=re.compile(
            r"\b[\w./-]+\.(?:csv|tsv|parquet)\b"
            r"|\bparquet files?\b",
            re.I,
        ),
        suppress=CODE_ADJACENT,
        message=(
            "Local tabular file (CSV/TSV/Parquet) analysis detected.\n"
            "duckdb skill (read-only SELECT/DESCRIBE/SUMMARIZE, runtime "
            "~/.codex/tools/duckdb/bin/duckdb) and qsv skill (fast CSV stats/validation, "
            "~/.codex/tools/qsv/bin/qsv) are installed -- prefer them over ad-hoc pandas "
            "scripts for local tabular files; read-only, no network."
        ),
    ),
    dict(
        id="doc-extract",
        intent=re.compile(
            r"\b(?:read(?:ing)?|extract(?:s|ing)?|convert(?:s|ing)?|summariz(?:e|es|ing))\b"
            r"|\bpull(?:ing)?\s+(?:the\s+|out\s+)?text\b"
            r"|\bwhat does\b[^?\n]{0,60}\bsay\b",
            re.I,
        ),
        # Standalone file-reference token only. Deliberately EXCLUDES .pdf and
        # .xlsx/.xlsm/.csv -- dedicated pdf/xlsx skills own those, and this
        # message must never fire for them.
        requires=re.compile(
            r"\b[\w./-]+\.(?:docx|doc|pptx|epub|eml|msg|odt|rtf)\b",
            re.I,
        ),
        suppress=CODE_ADJACENT,
        message=(
            "Local office/e-mail/e-book document (.docx/.doc/.pptx/.epub/.eml/.msg/.odt/"
            ".rtf) detected.\n"
            "markitdown skill converts these locally to Markdown for analysis (runtime "
            "~/.codex/tools/markitdown-venv/bin/markitdown); stdout only, no cloud services."
        ),
    ),
    dict(
        id="share-preflight",
        intent=re.compile(
            r"\b(?:shar(?:e|es|ing)|send(?:s|ing)?|export(?:s|ing)?|upload(?:s|ing)?"
            r"|hand(?:s|ing)?\s+over|post(?:s|ing)?)\b",
            re.I,
        ),
        # Either an external-audience phrase OR an explicit sensitive-data
        # token. No file-extension gate for this category by design.
        requires=re.compile(
            r"\bexternally\b|\bwith the client\b|\bwith the team\b|\bpublicly\b|\boutside\b"
            r"|\bPII\b|\bredact(?:ed|ing|ion)?\b|\bsanitiz(?:e|es|ing|ed|ation)\b"
            r"|\bscrub(?:s|bing|bed)?\b|\banonymi[sz](?:e|es|ing|ed|ation)\b",
            re.I,
        ),
        message=(
            "Share / send / export / upload / post outside this machine detected.\n"
            "presidio skill = redacted PII preview (offsets only, never values); gitleaks "
            "skill = redacted secret scan; run both locally BEFORE anything leaves the "
            "machine; \"no findings\" is not clearance."
        ),
    ),
    dict(
        id="design-ship-check",
        intent=re.compile(
            r"\b(?:ship(?:s|ping)?(?:\s+it)?|ready\s+to\s+ship|good\s+to\s+go"
            r"|good\s+enough|does\s+(?:this|it)\s+look|is\s+(?:this|it)\s+(?:good|ready|right|on.?brand)"
            r"|review\s+(?:this|the|my))\b",
            re.I,
        ),
        requires=re.compile(
            r"\b(?:design|page|landing\s*page|homepage|hero|UI|mockup|layout|screen"
            r"|site|deck|slide|carousel|creative|banner|figma|visual)\b",
            re.I,
        ),
        message=(
            "User-facing visual surface heading toward ship detected.\n"
            "design-judge skill governs BEFORE any visual surface ships: render -> lens "
            "panel (mechanism + trust-and-proof mandatory) -> verdict; an errored lens is "
            "an OPEN finding, never a pass. It does NOT reliably self-trigger -- invoke "
            "/design-judge rather than waiting. It greps references/ai-slop-checklist.md (87 tells)."
        ),
    ),
    dict(
        id="register-exec",
        intent=re.compile(
            r"\b(?:draft(?:s|ing)?|writ(?:e|es|ing)|repl(?:y|ies|ying)|updat(?:e|es|ing)"
            r"|messag(?:e|es|ing)|send(?:s|ing)?|tell(?:s|ing)?|ping|note)\b"
            r"|\blet\s+\w+\s+know\b",
            re.I,
        ),
        requires=re.compile(
            r"\bCEO\b|\bexec(?:utive)?s?\b|\bleadership\b|\bboard\b"
            r"|\binvestors?\b|\bthe\s+client\b|\bfounder\b|\bchief\b",
            re.I,
        ),
        suppress=CODE_ADJACENT,
        message=(
            "Drafting a message/update for a reader NOT in the session (exec/board/client).\n"
            "fable-judgment section 3 register rule: the reader's DISTANCE from the work "
            "sets the register, not the channel or message length. A CEO/board/client "
            "update gets answer-first MBB structure (outcome -> verified-how -> residual "
            "risk if real) EVEN as a short Slack ping. 'It is just a status ping' is the "
            "misroute -- brevity is not the register, shared session context is. Never "
            "claim verified without naming the artifact."
        ),
    ),
]


def _extract_prompt(payload: dict) -> str:
    # Same defensive key fallback as service-routing-guard -- never crash on a
    # payload-shape surprise.
    for key in ("prompt", "user_prompt", "text", "message"):
        val = payload.get(key)
        if isinstance(val, str):
            return val
    return ""


def match_categories(prompt: str) -> list:
    """Return the list of matching category dicts. Importable so the
    self-test can reason about WHICH category fired, not just that something
    did. No global code veto here -- see the CRITICAL DESIGN DIFFERENCE
    section in the module docstring; each category's own requires/suppress
    gates are the only filtering."""
    hits = []
    for c in CATEGORIES:
        if not c["intent"].search(prompt):
            continue
        req = c.get("requires")
        if req is not None and not req.search(prompt):
            continue
        sup = c.get("suppress")
        if sup is not None and sup.search(prompt):
            continue
        hits.append(c)
    return hits


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        prompt = _extract_prompt(payload) if isinstance(payload, dict) else ""
        if not prompt:
            return  # no recognizable prompt -> silent, per contract

        hits = match_categories(prompt)
        if not hits:
            return  # no category match -> silent, per contract

        header = (
            "skill-routing-guard (UserPromptSubmit hook, non-blocking reminder-only -- "
            "third hook in the autoload-judgment / fleet-delegation-guard / "
            "skill-routing-guard family):\n\n"
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": header + "\n\n---\n\n".join(c["message"] for c in hits),
            }
        }))
    except Exception:
        # Never error the turn. A malformed/unexpected payload is treated the
        # same as "no match": silent, exit 0.
        return


if __name__ == "__main__":
    main()

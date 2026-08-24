#!/usr/bin/env python3
"""SessionStart hook: deterministically inject the fable-judgment skill body.

Closes the gap both skills document ("the harness cannot auto-load a skill by
detecting the model"): instead of detecting anything, inject the judgment layer
into every session's starting context. Companion to
~/.claude/skills/fable-judgment/SKILL.md (source of truth: edits there are
picked up automatically; this hook only reads, never copies).

2026-07-26 — INJECT THE JUDGMENT, NOT THE BOOKKEEPING. Two blocks are stripped
before injection because they cost tokens in EVERY session while teaching
nothing at decision time:
  1. YAML frontmatter — the description is for skill routing, not context.
  2. The version-header blockquote between the H1 and the first `## ` section —
     pure changelog. It had reached 35 of 159 lines (22%) by v5, and it grows by
     construction: the weekly maintenance task appends a version note every run.
     Stripping it here decouples changelog growth from per-session context cost
     permanently, so future maintenance passes can write as much version detail
     as they like at zero standing cost.
Only §1-§4 — the actual judgment — reaches context. Nothing that changes a
decision is removed; if a future section is added it is injected automatically,
because the strip is anchored on "everything before the first `##`".
"""
import json
import re
from pathlib import Path

SKILL = Path.home() / ".claude/skills/fable-judgment/SKILL.md"


def _strip_version_header(body: str) -> str:
    """Drop the changelog blockquote sitting between the H1 and the first section.

    Conservative by construction: only contiguous blockquote/blank lines are
    dropped, and only before the first `## ` heading. If the file's shape ever
    changes (no H1, no `## `, prose instead of a blockquote), nothing is removed
    and the full body is injected — failing toward MORE context, never less.
    """
    lines = body.split("\n")
    try:
        h1 = next(i for i, ln in enumerate(lines) if ln.startswith("# "))
        first_section = next(i for i, ln in enumerate(lines) if ln.startswith("## "))
    except StopIteration:
        return body
    if first_section <= h1:
        return body

    between = lines[h1 + 1:first_section]
    # Only strip if this really is a changelog blockquote and nothing else.
    if not any(ln.startswith(">") for ln in between):
        return body
    if any(ln.strip() and not ln.startswith(">") for ln in between):
        return body  # unexpected prose mixed in -> leave it alone

    kept = lines[:h1 + 1] + ["", "*(version history omitted from context — see SKILL.md)*", ""] + lines[first_section:]
    stripped = "\n".join(kept)

    # Self-check: the whole point of this function is to remove ONLY bookkeeping.
    # If the result has lost any judgment section, the strip logic is wrong for
    # this file's current shape — inject the untouched body instead of silently
    # serving a mutilated judgment layer. The integrity canary in CLAUDE.md only
    # detects a TOTAL failure to inject; it cannot see a partial one, so this is
    # the only thing standing between a bad edit here and a session that thinks
    # it has the judgment layer while missing half of it.
    for marker in ("## 1.", "## 2.", "## 3.", "## 4."):
        if marker not in stripped:
            return body
    return stripped


def main() -> None:
    try:
        text = SKILL.read_text(encoding="utf-8")
    except Exception:
        return  # skill missing/unreadable -> stay silent, never break startup

    # strip YAML frontmatter; the description is for routing, not context
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()
    body = _strip_version_header(body)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "fable-judgment skill (auto-loaded by SessionStart hook — "
                "deterministic, model-independent):\n\n" + body
            ),
        }
    }))


if __name__ == "__main__":
    main()

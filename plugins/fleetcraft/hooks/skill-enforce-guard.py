#!/usr/bin/env python3
"""skill-enforce-guard (PreToolUse / Bash|Grep|Glob): makes two skill-shaped
preconditions actually happen instead of staying an unfired reminder.

Companion to tool-routing-guard: the same deny-once-then-allow contract, applied to
two procedural preconditions instead of documentation routing.

WHY THIS EXISTS: a reminder alone does not reliably cause a model-selected skill
to actually load for a procedural precondition. This hook applies the same
deny-once-then-allow contract tool-routing-guard already uses for its optional
documentation-routing lane, narrowed to two lanes:

  1. gitleaks lane  -- the first `git commit` / `git push` of a session. A
     redacted secret preflight should run before committing or pushing source
     or config changes.
  2. graphify lane  -- the first broad recursive search (rg/ag/ack, `grep -r`,
     or the Grep/Glob tools) of a session, in a cwd that has a graphify-out/
     index. Querying the graph first answers structural questions for a
     fraction of the tokens of grepping around.

DEFAULT = reminder via additionalContext, same as tool-routing-guard's default.
Opt-in enforcement (`preflight_enforce`) denies the FIRST matching command in a
session and allows every retry, including the identical command replayed
immediately after the deny -- the marker is written before the decision is
returned, so the retry's own `_fired_before` check already reads "already
fired" and lets it through.

COMMAND-POSITION ANCHORING: matches are anchored to the start of a shell
segment (start of string, or immediately after `;`, `&`, `|`, `(`, `&&`, `||`).
Without this, a quoted `git commit` inside a `claude -p "... git commit ..."`
argument would false-positive, because the literal text sits inside a quoted
argument rather than being an executed command. That anchoring is deliberately
identical in shape to the source this hook was ported from, which hit exactly
this false positive on its first live test.

ERROR CONTRACT: silent on any internal error, exit 0 -- same choice as the
routing guards (tool-routing-guard, fleet-delegation-guard's fail-open paths).
A silently-dead reminder costs one missed nudge, not a broken gate.

KILL SWITCH: `preflight_enforce` unset or false downgrades both denies to
reminders (`CLAUDE_PLUGIN_OPTION_PREFLIGHT_ENFORCE`).
STATE: marker files under STATE_DIR keyed on session_id, so each lane fires at
most once per session (override the dir with CLAUDE_SKILL_ENFORCE_STATE_DIR
for the self-test, matching the tool-routing-guard test pattern).
"""
import json
import os
import pathlib
import re
import sys

STATE_DIR = os.environ.get(
    "CLAUDE_SKILL_ENFORCE_STATE_DIR", "/tmp/claude-skill-enforce-guard"
)


def enforce_enabled() -> bool:
    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_PREFLIGHT_ENFORCE", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


ENFORCE = enforce_enabled()


def gitleaks_name() -> str:
    """Name a gitleaks binary path if the plugin option supplies one,
    otherwise point at the project so the reminder never invents a path this
    machine does not actually have."""
    path = os.environ.get("CLAUDE_PLUGIN_OPTION_GITLEAKS_PATH", "").strip()
    return path if path else "github.com/gitleaks/gitleaks"


MSG_GITLEAKS = (
    "skill-enforce-guard: this is the first commit/push of the session. Run a "
    "redacted secret preflight on the staged diff first -- {gitleaks} -- then "
    "re-run this exact command; the retry always passes. Never commit or push "
    "source/config changes without the preflight. Findings stay redacted; "
    "'no findings' is not clearance. This reminder fires at most once per session."
)

MSG_GRAPHIFY = (
    "skill-enforce-guard: this repo has a graphify-out/ index. Query the graph "
    "first -- it answers structural questions (what calls what, where a symbol "
    "lives, what depends on X) for a fraction of the tokens of a broad search -- "
    "then re-run this search if the graph did not answer it; the retry always "
    "passes. Check index freshness (`git log -1` vs built_at_commit in "
    "graphify-out/graph.json) before trusting it. Once per session."
)

MSG_GITLEAKS_DENY = (
    "skill-enforce-guard DENIED this commit/push because optional enforcement is "
    "enabled. Run a redacted secret preflight on the staged diff first -- {gitleaks} "
    "-- then retry this exact command; the one-per-session gate then permits it."
)

MSG_GRAPHIFY_DENY = (
    "skill-enforce-guard DENIED this broad search because optional enforcement is "
    "enabled and a graphify-out/ index exists in this cwd. Query the graph first, "
    "then retry this exact search; the one-per-session gate then permits it."
)

# Anchor to a COMMAND position: start of line, or after ; && || | ( or newline.
# Without this, a quoted `git commit` inside a `claude -p "... git commit ..."`
# argument false-positives, because the literal text sits inside a quoted
# argument rather than being an executed command.
GIT_WRITE = re.compile(
    r"(?:^|[;&|(]|&&|\|\|)\s*git\s+(?:-{1,2}\S+(?:\s+\S+)?\s+)*(commit|push)\b"
)

BROAD_SEARCH = re.compile(
    r"(?:^|[;&|(]|&&|\|\|)\s*(?:rg|ag|ack)\b"           # ripgrep/ag/ack: recursive by default
    r"|(?:^|[;&|(]|&&|\|\|)\s*grep\s+(?:-\S*[rR]\S*\s)"  # grep -r / -R / -rn etc.
)


def _session_key(payload: dict) -> str:
    sid = payload.get("session_id")
    if isinstance(sid, str) and sid:
        return sid
    return "unknown-session"


def _fired_before(key: str, lane: str) -> bool:
    """True if this lane already fired this session; records the firing
    otherwise. Any filesystem error reads as 'already fired' -- fail toward
    silence, matching tool-routing-guard's error contract."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        marker = os.path.join(STATE_DIR, f"{key}.{lane}")
        if os.path.exists(marker):
            return True
        with open(marker, "w"):
            pass
        return False
    except Exception:
        return True


def _graphify_repo(payload: dict) -> bool:
    cwd = payload.get("cwd") or os.getcwd()
    try:
        return (pathlib.Path(cwd) / "graphify-out").is_dir()
    except Exception:
        return False


def _emit(reminder: str, deny_reason: str) -> None:
    if ENFORCE:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": deny_reason,
            }
        }))
    else:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": reminder,
            }
        }))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return
        key = _session_key(payload)
        tool = payload.get("tool_name") or ""
        tool_input = payload.get("tool_input") or {}

        if tool == "Bash":
            command = tool_input.get("command") if isinstance(tool_input, dict) else ""
            command = command if isinstance(command, str) else ""
            if GIT_WRITE.search(command) and "gitleaks" not in command:
                if not _fired_before(key, "gitleaks"):
                    _emit(
                        MSG_GITLEAKS.format(gitleaks=gitleaks_name()),
                        MSG_GITLEAKS_DENY.format(gitleaks=gitleaks_name()),
                    )
                return
            if (
                BROAD_SEARCH.search(command)
                and "graphify" not in command
                and _graphify_repo(payload)
                and not _fired_before(key, "graphify")
            ):
                _emit(MSG_GRAPHIFY, MSG_GRAPHIFY_DENY)
            return

        if tool in ("Grep", "Glob"):
            if _graphify_repo(payload) and not _fired_before(key, "graphify"):
                _emit(MSG_GRAPHIFY, MSG_GRAPHIFY_DENY)
            return
    except Exception:
        # Silent on any internal error, per the error contract in the docstring.
        return


if __name__ == "__main__":
    main()

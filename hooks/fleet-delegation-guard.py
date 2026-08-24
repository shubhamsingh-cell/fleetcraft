#!/usr/bin/env python3
"""fleet-orchestrator delegation guard (PreToolUse / Bash).

Installed 2026-07-07 with explicit user approval; hardened 2026-07-15 per the
completeness audit. Non-blocking: never denies, only injects a reminder into
model context when the main loop is about to run a deploy-shaped command
directly — the exact moment the fleet-orchestrator skill says to consider
delegating. Companion to ~/.claude/skills/fleet-orchestrator/SKILL.md.
"""
import json
import re
import sys

# 2026-07-15: extended beyond bare git shapes — the original regex silently
# missed `git -C <worktree> push` (this user's highest-frequency deploy shape),
# release/deploy commands, and Slack webhook sends.
SHAPES = re.compile(
    r"git\s+(-C\s+\S+\s+)?(commit|push)\b"
    r"|git worktree add"
    r"|gh (pr (create|merge)|release create)"
    r"|vercel\b.*(--prod|\bdeploy\b)"
    r"|render\s+deploy"
    r"|hooks\.slack\.com"
)

# 2026-07-26: second shape class, added because fable-judgment §4's 2026-07-17
# entry ("an instruction to a subagent is a request, not a mechanism") had NO
# enforcement — the rule lived only in prose, which is precisely the failure it
# describes. A long-lived run cannot be delegated: a subagent's process dies
# when its turn ends, and no wording in the brief prevents that. Kept narrow on
# purpose — these are the shapes that actually outlive a turn.
LONG_RUN = re.compile(
    r"ship[\w./-]*\.sh\b"
    r"|ship_from_worktree"
    r"|\bpytest\b"
    r"|\b(npm|pnpm|yarn)\s+(run\s+)?(build|test|e2e)\b"
    r"|alembic\s+upgrade"
    r"|\bmake\s+(build|test|deploy)\b"
    r"|docker\s+(build|compose\s+up)"
)

_LONG_RUN_MSG = (
    "fleet-orchestrator guard: this Bash call is a LONG-LIVED RUN "
    "(ship script / full suite / build / migration). This shape is NOT delegable, "
    "and that is the opposite of the deploy-shaped rule: a subagent's process dies "
    "when its turn ends, so a delegated long run fails silently mid-flight "
    "(precedent: ship_from_worktree.sh died with the subagent 2026-07-16; a sharper "
    "brief did not fix it and the next one died again 2026-07-17, silent for 45 min). "
    "If you are the MAIN-LOOP ORCHESTRATOR: run it YOURSELF as harness-tracked work "
    "(Bash with run_in_background, which persists across turns and re-invokes you on "
    "exit, plus a Monitor/poll loop) and delegate only the prep — edits, staging, the "
    "diff, the go/no-go read. Do NOT hand the run itself to a subagent. "
    "If you are a SUBAGENT and this run was delegated to you: that delegation was the "
    "mistake — do NOT background it. Either run it strictly in the foreground and do "
    "not end your turn until it exits, or stop and report back that the run must be "
    "executed by the orchestrator."
)

# 2026-08-13: gitleaks preflight line, factored out so both the full
# main-loop message and the subagent-only message (below) can share the exact
# same sentence instead of drifting apart over future edits.
_GITLEAKS_PREFLIGHT = (
    "Before any commit or push that includes new or modified source/config, "
    "the gitleaks skill (runtime ~/.codex/tools/gitleaks/bin/gitleaks) offers "
    "a redacted local secret preflight — run it on the staged diff if it "
    "hasn't been run this session; findings stay redacted."
)

_DEPLOY_MSG = (
    "fleet-orchestrator guard: this Bash call is deploy/publish-shaped "
    "(commit/push/PR/release/deploy/webhook). "
    "If you are the MAIN-LOOP ORCHESTRATOR (not a delegated subagent): per "
    "~/.claude/skills/fleet-orchestrator/SKILL.md, mechanical multi-step "
    "execution (edit+commit+push, worktree publish, build+deploy) should be "
    "delegated to a Sonnet subagent — especially if an identically-shaped "
    "task was already delegated this session. Delegate unless a named "
    "exemption applies (live production incident; or restating context "
    "would cost more than the task) — and if exempt, say so explicitly. "
    "If this ships a USER-FACING VISUAL SURFACE, /design-judge must have run first "
    "(render -> lens panel -> verdict; mechanism and trust-and-proof lenses are "
    "mandatory, and an errored lens is an OPEN finding, never a pass). "
    "If you are a SUBAGENT executing a delegated brief: ignore this "
    "reminder and proceed. " + _GITLEAKS_PREFLIGHT
)

# 2026-08-13: the deploy-shaped + subagent branch used to return silently (see
# the in_subagent check below) — correct for the delegation nag, since a
# subagent doing the push IS the desired end state. But it threw away the
# gitleaks preflight reminder along with it. A subagent executing a delegated
# push is exactly who should run the preflight; it just shouldn't be nagged
# about delegation on top of it. Short and gitleaks-only, on purpose.
_SUBAGENT_DEPLOY_MSG = "fleet-orchestrator guard: " + _GITLEAKS_PREFLIGHT


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Do NOT go silent here. A guard that fails quietly is indistinguishable
        # from a guard that saw nothing worth flagging — it would stop guarding
        # forever (e.g. if the payload shape ever changes) and nobody would know.
        # The skill's own stance is "fail toward reminding — a false positive is
        # harmless because the text tells subagents to ignore it", so on a parse
        # failure we still emit, and we say the parse failed so it is visible.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    "fleet-orchestrator guard: could not parse this tool call's payload, "
                    "so shape detection did NOT run — treat this as an unchecked call, not "
                    "a cleared one. If this is a mechanical multi-step task (edit+commit+push, "
                    "build+deploy) apply the delegation rule yourself; if it is a long-lived "
                    "run (ship script, full suite, migration), the orchestrator runs it as "
                    "harness-tracked work rather than delegating it. If this message repeats, "
                    "the guard needs repair: ~/.claude/hooks/fleet-delegation-guard.py"
                ),
            }
        }))
        return

    cmd = (payload.get("tool_input") or {}).get("command") or ""
    is_long_run = bool(LONG_RUN.search(cmd))
    is_deploy = bool(SHAPES.search(cmd))
    if not (is_long_run or is_deploy):
        return

    # Subagent detection differs by shape, and the asymmetry is the whole point:
    #   deploy-shaped  -> a subagent doing the push IS the desired end state; don't nag.
    #   long-run       -> a subagent running it IS the bug; nag it hardest. This is the
    #                     only branch that can catch the 2026-07-16/17 failure in the act.
    # Primary discriminator: agent_id (also stops false nags on Workflow-spawned
    # agents); transcript-path check kept as backup.
    in_subagent = bool(payload.get("agent_id")) or "/subagents/" in (
        payload.get("transcript_path") or ""
    )
    if is_deploy and not is_long_run and in_subagent:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": _SUBAGENT_DEPLOY_MSG,
            }
        }))
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": _LONG_RUN_MSG if is_long_run else _DEPLOY_MSG,
        }
    }))


if __name__ == "__main__":
    main()

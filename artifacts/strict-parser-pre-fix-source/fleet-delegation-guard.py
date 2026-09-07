#!/usr/bin/env python3
"""PreToolUse guard with explicit audit and strict modes.

Audit mode (the default) contributes context for the *next* model decision and
never asserts that it prevented the current command.  Strict mode asks the
user before a matching publish action.  Claude Code performs that pause via a
real ``permissionDecision: ask``; it is not merely an advisory message.
"""

from __future__ import annotations

import os
from typing import Iterable

from fleet_hook_utils import command_from_payload, command_segments, command_substitutions, executable_tokens, hook_output, lexer_failed, read_json, unsupported_shell_construct


AUDIT = "audit"
STRICT = "strict"
INVALID = "invalid"
MAX_NESTED_SHELL_DEPTH = 64


def configured_mode() -> str:
    """Read plugin configuration defensively; invalid nonempty values fail closed."""
    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_DELEGATION_MODE", AUDIT).strip().lower()
    if not raw:
        return AUDIT
    return raw if raw in {AUDIT, STRICT} else INVALID


def _git_action(tokens: list[str]) -> str | None:
    if not tokens or tokens[0] != "git":
        return None
    options_with_values = {"-C", "-c", "--git-dir", "--work-tree", "--config-env"}
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return None
        if token in options_with_values:
            index += 2
            continue
        if token.startswith(("-C", "-c")) and len(token) > 2:
            index += 1
            continue
        if any(token.startswith(prefix + "=") for prefix in ("--git-dir", "--work-tree", "--config-env")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        # The first non-option token selects the git subcommand.  A shell
        # expansion here changes what executes, unlike a dynamic branch name.
        if "$" in token:
            return "dynamic git action"
        if token not in {"commit", "push"}:
            return None
        before_double_dash = _git_flags_before_double_dash(token, tokens[index + 1 :])
        if any(argument in {"--help", "-h", "--version"} for argument in before_double_dash):
            return None
        # `-n` is a dry-run only for the git subcommands where git documents
        # it as such. For `git commit -n` it means --no-verify and remains a
        # guarded, side-effecting action.
        if token == "push" and any(argument in {"--dry-run", "-n"} for argument in before_double_dash):
            return None
        return token
    return None


def _git_flags_before_double_dash(action: str, arguments: list[str]) -> list[str]:
    """Return real flags, excluding required option values and pathspecs.

    A value can look exactly like `--help` or `--dry-run`; treating it as a
    flag would convert a real commit/push into a false safe exemption. This is
    intentionally a small, explicit parser for the supported guarded actions,
    not an attempt to implement Git's full option grammar.
    """
    value_options = {
        "commit": {
            "-m", "-F", "-C", "-c", "--message", "--file",
            "--reuse-message", "--reedit-message", "--fixup", "--squash",
            "--trailer", "--pathspec-from-file",
        },
        "push": {
            "-o", "-u", "--push-option", "--set-upstream", "--receive-pack",
            "--exec", "--repo",
        },
    }
    flags: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            break
        if argument in value_options[action]:
            index += 2
            continue
        # Attached short values (`-mmessage`, `-ooption`) and `--flag=value`
        # cannot be an exact help/dry-run flag themselves.
        if (
            (action == "commit" and argument.startswith(("-m", "-F", "-C", "-c")) and len(argument) > 2)
            or (action == "push" and argument.startswith(("-o", "-u")) and len(argument) > 2)
            or any(argument.startswith(option + "=") for option in value_options[action] if option.startswith("--"))
        ):
            index += 1
            continue
        flags.append(argument)
        index += 1
    return flags


def _gh_action(tokens: list[str]) -> str | None:
    if not tokens or tokens[0] != "gh":
        return None
    if any(token in {"--help", "-h", "--version"} for token in tokens[1:]):
        return None
    options_with_values = {"-R", "--repo", "--hostname", "--config"}
    meaningful: list[str] = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in options_with_values:
            index += 2
            continue
        if token.startswith("--repo=") or token.startswith("--hostname="):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        meaningful.append(token)
        index += 1
    if "pr" in meaningful and ("create" in meaningful or "merge" in meaningful):
        return "pull request"
    if "release" in meaningful and "create" in meaningful:
        return "release"
    return None


def classify_command(command: str, depth: int = 0) -> set[str]:
    """Classify executable command segments, not quoted examples or `echo` text."""
    matches: set[str] = set()
    # Parsing does not silently stop at a shallow nesting limit. If a hostile
    # command exceeds this resource boundary, surface an explicit match so
    # strict mode asks rather than allowing an unknown nested command through.
    if depth >= MAX_NESTED_SHELL_DEPTH:
        return {"unparseable nested shell construct"}
    if lexer_failed(command) or unsupported_shell_construct(command):
        matches.add("unparseable shell construct")
    for substitution in command_substitutions(command):
        matches.update(classify_command(substitution, depth + 1))
    for segment in command_segments(command):
        tokens = executable_tokens(segment)
        if not tokens:
            continue
        if tokens[0] == "__fleetcraft_unparseable_shell__":
            matches.add("unparseable shell construct")
            continue
        # Shell control/group tokens precede the command they execute. They
        # are not quoted literals here: shlex has already split real segments.
        while tokens and tokens[0] in {"{", "(", "then", "do", "!"}:
            tokens.pop(0)
        if not tokens:
            continue
        program = tokens[0].rsplit("/", 1)[-1].lower()
        tokens[0] = program
        if program.startswith("$") or "${" in program:
            matches.add("dynamic executable")
            continue
        if program in {"bash", "sh", "zsh", "pwsh", "powershell", "powershell.exe"}:
            # Shell switches such as `-c` decide whether a following string is
            # executed.  A dynamic token in this control position cannot be
            # proven inert by this lightweight classifier.
            if any("$" in token for token in tokens[1:]):
                matches.add("dynamic shell control")
                continue
            command_flags = {"-command"}
            for index, token in enumerate(tokens[1:], start=1):
                is_short_command = token.startswith("-") and not token.startswith("--") and "c" in token[1:].lower()
                if token.lower() in command_flags or is_short_command:
                    argument = index + 1
                    if argument < len(tokens) and tokens[argument] == "--":
                        argument += 1
                    if argument < len(tokens):
                        matches.update(classify_command(tokens[argument], depth + 1))
                    break
            continue
        git_action = _git_action(tokens)
        if git_action:
            matches.add(f"git {git_action}")
            continue
        gh_action = _gh_action(tokens)
        if gh_action:
            matches.add(f"gh {gh_action}")
            continue
        lower_tokens = {token.lower() for token in tokens[1:]}
        if any(token in {"--help", "-h", "--version", "version"} for token in tokens[1:]):
            continue
        if program in {"vercel", "render", "netlify", "fly", "railway"} and (
            "deploy" in lower_tokens or (program == "vercel" and "--prod" in lower_tokens)
        ):
            matches.add(f"{program} deploy")
        elif program in {"curl", "http", "wget"} and any("hooks.slack.com" in token for token in tokens):
            matches.add("webhook send")
    return matches


def is_subagent(payload: dict) -> bool:
    return bool(payload.get("agent_id") or payload.get("agent_type"))


def malformed_command_payload(payload: dict) -> bool:
    """Detect nonempty Bash payloads we cannot safely classify in strict mode."""
    if not payload:
        return False
    tool_input = payload.get("tool_input")
    if "tool_input" in payload and not isinstance(tool_input, dict):
        return True
    if isinstance(tool_input, dict) and "command" in tool_input and not isinstance(tool_input["command"], str):
        return True
    return "command" in payload and not isinstance(payload["command"], str)


def context_for(actions: Iterable[str], mode: str, subagent: bool) -> str:
    listed = ", ".join(sorted(actions))
    base = (
        f"Fleetcraft {mode} delegation guard matched: {listed}. "
        "This hook classified the command before execution. "
    )
    if mode == STRICT:
        return base + (
            "Strict mode requests user confirmation for this publish-shaped action. "
            "Confirm the exact target, approval, verification evidence, and secret preflight."
        )
    if subagent:
        return base + (
            "Audit mode does not block the current call. You are already a delegated agent: "
            "record the observed preflight and terminal result; do not claim deploy success from a push."
        )
    return base + (
        "Audit mode does not block the current call. Before the next irreversible step, "
        "check whether bounded execution should be delegated, verify the exact target and approval, "
        "and run a redacted secret preflight when source/config changed."
    )


def main() -> None:
    payload = read_json()
    mode = configured_mode()
    if mode == INVALID:
        hook_output("PreToolUse", "Fleetcraft delegation_mode is invalid; confirmation is required until configuration is set to audit or strict.", permissionDecision="ask", permissionDecisionReason="Invalid nonempty delegation_mode fails closed.")
        return
    if payload is None:
        if mode == STRICT:
            hook_output("PreToolUse", "Fleetcraft strict delegation guard could not parse this command payload; confirmation is required until it can be inspected.", permissionDecision="ask", permissionDecisionReason="Malformed command payload cannot be safely classified in strict mode.")
        else:
            hook_output(
                "PreToolUse",
                "Fleetcraft audit delegation guard could not parse this command payload. Audit mode does not block the current call; inspect the exact command and approval before an irreversible step.",
            )
        return
    if mode == STRICT and malformed_command_payload(payload):
        hook_output("PreToolUse", "Fleetcraft strict delegation guard received a malformed command payload; confirmation is required until it can be inspected.", permissionDecision="ask", permissionDecisionReason="Malformed command payload cannot be safely classified in strict mode.")
        return
    actions = classify_command(command_from_payload(payload))
    if not actions:
        return
    context = context_for(actions, mode, is_subagent(payload))
    if mode == STRICT:
        hook_output(
            "PreToolUse",
            context,
            permissionDecision="ask",
            permissionDecisionReason="Fleetcraft strict mode requires confirmation for a publish-shaped command.",
        )
        return
    hook_output("PreToolUse", context)


if __name__ == "__main__":
    main()

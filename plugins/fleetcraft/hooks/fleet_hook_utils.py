"""Small, dependency-free helpers shared by Fleetcraft hook entrypoints."""

from __future__ import annotations

import json
import re
import shlex
import sys
from typing import Any, Iterator


def read_json() -> dict[str, Any] | None:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def command_from_payload(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
        return tool_input["command"]
    return payload.get("command") if isinstance(payload.get("command"), str) else ""


def prompt_from_payload(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_prompt", "text", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def hook_output(event: str, context: str, *, system_message_text: str | None = None, **decision: str) -> None:
    """Emit exactly one JSON object for one hook invocation.

    Hooks may need to show a warning and provide hook context together.  They
    must remain one JSON document: Claude Code treats stdout as the hook
    response, and newline-delimited independent objects are not a response
    schema.
    """
    output: dict[str, Any] = {"hookEventName": event, "additionalContext": context}
    output.update(decision)
    envelope: dict[str, Any] = {"hookSpecificOutput": output}
    if system_message_text is not None:
        envelope["systemMessage"] = system_message_text
    print(json.dumps(envelope, ensure_ascii=False))


def system_message(message: str) -> None:
    """Show a bounded user-facing warning without pretending context loaded."""
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))


def command_segments(command: str) -> Iterator[list[str]]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return
    segment: list[str] = []
    for token in tokens + [";"]:
        if token and all(char in ";&|" for char in token):
            if segment:
                yield segment
                segment = []
        else:
            segment.append(token)


def lexer_failed(command: str) -> bool:
    """Whether the segment lexer cannot consume this shell input.

    The classifier is deliberately not a shell interpreter.  A quote or escape
    error means its result is incomplete, so strict mode must ask rather than
    silently treating that command as safe.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        list(lexer)
    except ValueError:
        return True
    return False


def command_substitutions(command: str) -> Iterator[str]:
    """Yield ``$(...)`` and backtick bodies that a shell will execute.

    ``shlex`` intentionally treats command substitutions as ordinary words, so
    inspect them separately. Single-quoted text is literal; double-quoted text
    still performs substitution. Nested substitutions are retained as part of
    their parent body and are discovered by the recursive classifier.
    """
    index = 0
    single_quoted = False
    double_quoted = False
    while index < len(command):
        char = command[index]
        if char == "\\" and not single_quoted:
            index += 2
            continue
        if char == "'" and not double_quoted:
            single_quoted = not single_quoted
            index += 1
            continue
        if char == '"' and not single_quoted:
            double_quoted = not double_quoted
            index += 1
            continue
        if not single_quoted and not double_quoted and char == "#" and (index == 0 or command[index - 1].isspace()):
            newline = command.find("\n", index)
            index = len(command) if newline < 0 else newline + 1
            continue
        if not single_quoted and char == "`":
            end = index + 1
            while end < len(command):
                if command[end] == "\\":
                    end += 2
                    continue
                if command[end] == "`":
                    yield command[index + 1 : end]
                    index = end + 1
                    break
                end += 1
            else:
                index += 1
            continue
        if not single_quoted and command.startswith("$(", index):
            start = index + 2
            depth = 1
            cursor = start
            nested_single_quote = False
            nested_double_quote = False
            while cursor < len(command) and depth:
                nested = command[cursor]
                if nested == "\\" and not nested_single_quote:
                    cursor += 2
                    continue
                if nested == "'" and not nested_double_quote:
                    nested_single_quote = not nested_single_quote
                elif nested == '"' and not nested_single_quote:
                    nested_double_quote = not nested_double_quote
                elif not nested_single_quote and not nested_double_quote and nested == "(":
                    depth += 1
                elif not nested_single_quote and not nested_double_quote and nested == ")":
                    depth -= 1
                cursor += 1
            if depth == 0:
                yield command[start : cursor - 1]
                index = cursor
                continue
        index += 1


_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def unsupported_shell_construct(command: str) -> bool:
    """Return true for shell grammar this lightweight classifier cannot prove safe.

    This is deliberately conservative. It is used by strict mode as a reason to
    ask for confirmation, never as a claim of sandboxing or full shell parsing.
    Quoted examples and comments are removed before checking control grammar.
    """
    visible: list[str] = []
    index = 0
    single = double = False
    while index < len(command):
        char = command[index]
        if char == "\\" and not single:
            visible.append(" ")
            index += 2
            continue
        if char == "'" and not double:
            single = not single
            visible.append(" ")
        elif char == '"' and not single:
            double = not double
            visible.append(" ")
        elif not single and not double and char == "#" and (index == 0 or command[index - 1].isspace()):
            newline = command.find("\n", index)
            index = len(command) if newline < 0 else newline + 1
            continue
        elif single or double:
            visible.append(" ")
        else:
            visible.append(char)
        index += 1
    text = "".join(visible)
    if "\n" in text:
        return True
    # Grouping, functions, and control grammar need a real shell parser. `$(`
    # is classified recursively elsewhere and is not itself unknown here.
    if re.search(r"(^|[;|&]\s*)[A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)", text):
        return True
    if re.search(r"\b(?:function|if|then|elif|else|fi|case|esac|for|while|until|do|done|eval)\b", text):
        return True
    if re.search(r"(?:^|[;|&\s])(?:\{|\})(?:[;|&\s]|$)", text):
        return True
    # Parentheses not belonging to a simple command substitution are
    # grouping/subshells. Nested substitutions are separately bounded by the
    # recursive classifier, so stripping the simple form here avoids treating
    # `echo $(git push)` as unknown.
    grouping_text = re.sub(r"\$\([^()]*\)", "", text)
    for char in grouping_text:
        if char in "()":
            return True
    return False


def executable_tokens(segment: list[str]) -> list[str]:
    tokens = list(segment)
    while tokens and _ASSIGNMENT.match(tokens[0]):
        tokens.pop(0)
    # These wrappers do not change the executable being invoked.  Treat `--`
    # as the end of wrapper options rather than consuming the executable as an
    # option argument (for example, `env -- git push`).
    while tokens and tokens[0].rsplit("/", 1)[-1] in {"command", "env", "sudo", "time", "nohup"}:
        wrapper = tokens.pop(0).rsplit("/", 1)[-1]
        while tokens and tokens[0].startswith("-"):
            option = tokens.pop(0)
            if option == "--":
                break
            # Only wrappers with documented option arguments consume a
            # following token.  `command -- git` and `env -- git` must leave
            # `git` intact as the executable.
            takes_value = {
                "env": {"-C", "-u", "--chdir", "--unset", "-S", "--split-string"},
                # The short options below take values on supported sudo
                # implementations. Consume them before identifying the
                # wrapped executable so a value cannot hide `git`/`gh`.
                "sudo": {"-u", "--user", "-g", "--group", "-h", "--host", "-p", "--prompt", "-r", "--role", "-t", "--type", "-C", "--close-from", "-D", "-R", "-T"},
                "time": {"-f", "--format", "-o", "--output"},
            }
            if option in takes_value.get(wrapper, set()) and tokens:
                value = tokens.pop(0)
                if wrapper == "env" and option in {"-S", "--split-string"}:
                    try:
                        # `env -S 'git push'` invokes the split value as the
                        # executable command. Expand it rather than treating
                        # it as an inert option argument.
                        tokens = shlex.split(value, posix=True) + tokens
                    except ValueError:
                        return ["__fleetcraft_unparseable_shell__"]
            elif wrapper == "time" and option.startswith("-"):
                # Implementations differ; unknown time options may consume the
                # next word, so never guess the executable.
                return ["__fleetcraft_unparseable_shell__"]
        while tokens and _ASSIGNMENT.match(tokens[0]):
            tokens.pop(0)
    return tokens

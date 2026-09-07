#!/usr/bin/env python3
"""TaskCompleted gate for tasks that explicitly opt into Fleetcraft evidence."""

from __future__ import annotations

import os
import re
import sys

from fleet_hook_utils import read_json


PLACEHOLDERS = {"", "-", "none", "n/a", "na", "todo", "tbd", "unknown", "pending", "test output", "clean install"}
EVIDENCE_PATTERN = re.compile(r"^artifact=(?P<artifact>[^;]+);\s*sha256=(?P<digest>[0-9a-f]{64})$")
VALIDATION_PATTERN = re.compile(r"(?i)^command=(?P<command>[^;]+);\s*result=(?P<result>pass|passed|success|0)$")


def field(description: str, label: str) -> str | None:
    match = re.search(rf"(?im)^[ \t]*{label}:[ \t]*(?P<value>[^\r\n]*)$", description)
    return match.group("value").strip() if match else None


def valid_evidence(value: str | None) -> bool:
    if value is None or value.lower() in PLACEHOLDERS:
        return False
    match = EVIDENCE_PATTERN.fullmatch(value)
    artifact = match.group("artifact").strip() if match else ""
    return bool(artifact and len(artifact) >= 8 and artifact.lower() not in PLACEHOLDERS)


def valid_validation(value: str | None) -> bool:
    if value is None or value.lower() in PLACEHOLDERS:
        return False
    match = VALIDATION_PATTERN.fullmatch(value)
    command = match.group("command").strip() if match else ""
    return bool(command and len(command) >= 4 and command.lower() not in PLACEHOLDERS)


def enabled() -> tuple[bool, bool]:
    """Return (enabled, invalid-option); invalid nonempty values fail safe."""
    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_COMPLETION_GATE", "false").strip().lower()
    if raw in {"", "0", "false", "no", "off"}:
        return False, False
    if raw in {"1", "true", "yes", "on"}:
        return True, False
    return True, True


def main() -> None:
    payload = read_json()
    enabled_option, invalid_option = enabled()
    if payload is None or not enabled_option:
        return
    description = payload.get("task_description")
    # Opt-in prevents the plugin from inventing evidence requirements for a
    # task that never claimed to be verified. Opted-in task briefs must carry
    # both explicit fields before Claude Code accepts completion.
    if not isinstance(description, str) or "[fleetcraft:verified]" not in description.lower():
        return
    evidence = field(description, "Evidence")
    validation = field(description, "Validation")
    invalid: list[str] = []
    if not valid_evidence(evidence):
        invalid.append("Evidence: artifact=<identity>; sha256=<64 lowercase hex characters>")
    if not valid_validation(validation):
        invalid.append("Validation: command=<executed command>; result=pass|passed|success|0")
    if invalid_option:
        invalid.append("a valid completion_gate option (true or false; invalid nonempty values fail safe)")
    if invalid:
        subject = payload.get("task_subject", "this task")
        print(
            f"Fleetcraft completion gate kept {subject!r} OPEN: verified tasks require {', '.join(invalid)} in task_description. Remaining semantic review is still required.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()

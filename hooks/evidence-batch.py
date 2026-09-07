#!/usr/bin/env python3
"""Optionally summarize tool batches without retaining prompt or result content."""
from __future__ import annotations

import os

from fleet_hook_utils import hook_output, read_json


def enabled() -> bool:
    return os.environ.get("CLAUDE_PLUGIN_OPTION_EVIDENCE_BATCH", "false").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    payload = read_json()
    if payload is None or not enabled():
        return
    calls = payload.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        return
    names = [call.get("tool_name") for call in calls if isinstance(call, dict) and isinstance(call.get("tool_name"), str)]
    if not names:
        return
    hook_output("PostToolBatch", f"Fleetcraft evidence batch: observed {len(names)} completed tool call(s): {', '.join(names[:8])}. Treat this as an evidence index, not proof of completion; name the relevant artifact and validation result.")


if __name__ == "__main__":
    main()

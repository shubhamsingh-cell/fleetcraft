#!/usr/bin/env python3
"""PostToolUse hook that reports harness-owned Agent model telemetry."""

from __future__ import annotations

from typing import Any

from fleet_hook_utils import hook_output, read_json


def model_values(response: Any) -> list[str]:
    if not isinstance(response, dict):
        return []
    values: list[str] = []
    resolved = response.get("resolvedModel")
    if isinstance(resolved, str):
        values.append(resolved)
    used = response.get("modelsUsed")
    if isinstance(used, list):
        values.extend(value for value in used if isinstance(value, str))
    return list(dict.fromkeys(values))


def main() -> None:
    payload = read_json()
    if payload is None:
        return
    models = model_values(payload.get("tool_response"))
    if not models:
        return
    hook_output(
        "PostToolUse",
        "Fleetcraft Agent runtime telemetry: "
        + ", ".join(models)
        + ". This is harness evidence about model resolution, not a quality verdict.",
    )


if __name__ == "__main__":
    main()

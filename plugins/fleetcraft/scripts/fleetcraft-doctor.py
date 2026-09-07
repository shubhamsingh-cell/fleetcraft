#!/usr/bin/env python3
"""Read-only release preflight for the Fleetcraft plugin package."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"


def check(condition: bool, message: str, errors: list[str]) -> None:
    print(("PASS" if condition else "FAIL") + " " + message)
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    for rel in (
        ".claude-plugin/plugin.json",
        "hooks/hooks.json",
        "hooks/judgment-kernel.md",
        "skills/doctor/SKILL.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
    ):
        check((ROOT / rel).is_file(), f"bundled {rel}", errors)
    try:
        manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        hooks = json.loads((HOOKS / "hooks.json").read_text())
        version = manifest.get("version")
        check(version == "0.1.1", "manifest v0.1.1", errors)
        check("hooks" not in manifest, "default hooks are not registered twice", errors)
        check("hooks" in hooks, "hook wiring is valid JSON", errors)
        handlers = [
            handler
            for groups in hooks.get("hooks", {}).values()
            for group in groups
            for handler in group.get("hooks", [])
        ]
        check(
            all("${CLAUDE_PLUGIN_ROOT}" not in handler.get("command", "") for handler in handlers),
            "plugin paths do not use shell-form commands",
            errors,
        )
        check(
            all(handler.get("args") for handler in handlers),
            "hook commands use exec-form args",
            errors,
        )
    except (OSError, json.JSONDecodeError, AttributeError, IndexError, TypeError) as exc:
        check(False, f"plugin JSON parses ({exc})", errors)
    try:
        kernel = (HOOKS / "judgment-kernel.md").read_text(encoding="utf-8")
        check(bool(kernel.strip()), "kernel is non-empty", errors)
        check(len(kernel) < 8_500, "kernel is below hook-context budget", errors)
    except OSError:
        check(False, "kernel is readable", errors)
    for script in HOOKS.glob("*.py"):
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except (OSError, SyntaxError) as exc:
            check(False, f"{script.name} compiles ({exc})", errors)
        else:
            check(True, f"{script.name} compiles", errors)
    print("Fleetcraft doctor: " + ("healthy" if not errors else f"{len(errors)} issue(s)"))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

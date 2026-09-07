#!/usr/bin/env python3
"""Install the marketplace package in isolation and inspect its exact cache payload."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_INSTALL_BYTES = 1_000_000
ALLOWED_TOP_LEVEL = {".claude-plugin", "LICENSE", "THIRD_PARTY_NOTICES.md", "agents", "hooks", "scripts", "skills"}
FORBIDDEN_PATHS = {".github", "artifacts", "tests", "pyproject.toml", "package.json", "package-lock.json", "node_modules"}


def run(command: list[str], *, env: dict[str, str], cwd: Path, input_text: str | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, input=input_text, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}{result.stderr}")
    return result.stdout


def inspect_install_package(install_path: Path) -> tuple[list[str], int]:
    top_level = {path.name for path in install_path.iterdir()}
    unexpected = sorted(top_level - ALLOWED_TOP_LEVEL)
    if unexpected:
        raise RuntimeError(f"plugin cache has unexpected top-level entries: {', '.join(unexpected)}")
    forbidden = sorted(path.relative_to(install_path).as_posix() for name in FORBIDDEN_PATHS for path in install_path.rglob(name))
    if forbidden:
        raise RuntimeError(f"plugin cache contains development payload: {', '.join(forbidden)}")
    files = sorted(path.relative_to(install_path).as_posix() for path in install_path.rglob("*") if path.is_file())
    size = sum((install_path / path).stat().st_size for path in files)
    if size > MAX_INSTALL_BYTES:
        raise RuntimeError(f"plugin install is unexpectedly large: {size} bytes (limit {MAX_INSTALL_BYTES})")
    return files, size


def main() -> int:
    claude = shutil.which("claude")
    if claude is None:
        print("Fleetcraft clean-install smoke requires the Claude Code CLI on PATH.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="fleetcraft-clean-install-") as temporary:
        config = Path(temporary) / "claude-config"
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        try:
            run([claude, "plugin", "marketplace", "add", str(ROOT)], env=env, cwd=ROOT)
            run([claude, "plugin", "install", "fleetcraft@fleetcraft"], env=env, cwd=ROOT)
            listing = run([claude, "plugin", "list"], env=env, cwd=ROOT)
            if "fleetcraft@fleetcraft" not in listing or "enabled" not in listing.lower():
                raise RuntimeError(f"installed plugin was not enabled:\n{listing}")
            installed = json.loads((config / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
            install_path = Path(installed["plugins"]["fleetcraft@fleetcraft"][0]["installPath"])
            if not install_path.is_dir() or config not in install_path.parents:
                raise RuntimeError(f"plugin cache path is missing or outside isolated config: {install_path}")
            installed_paths, install_size = inspect_install_package(install_path)
            run([sys.executable, "-B", str(install_path / "scripts" / "fleetcraft-doctor.py")], env=env, cwd=install_path)
            guarded = run(
                [sys.executable, "-B", str(install_path / "hooks" / "fleet-delegation-guard.py")],
                env={**env, "CLAUDE_PLUGIN_OPTION_DELEGATION_MODE": "strict"},
                cwd=install_path,
                input_text='{"tool_input":{"command":"git push origin main"}}',
            )
            if json.loads(guarded).get("hookSpecificOutput", {}).get("permissionDecision") != "ask":
                raise RuntimeError("installed strict delegation hook did not request confirmation")
        except (OSError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
            print(f"Fleetcraft clean-install smoke failed: {exc}", file=sys.stderr)
            return 1
    print(f"Fleetcraft clean-install smoke: passed (installed={install_path}; files={installed_paths}; bytes={install_size}; sparse runtime payload)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

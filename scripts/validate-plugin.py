#!/usr/bin/env python3
"""Strictly validate both Fleetcraft's marketplace and plugin manifests."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "fleetcraft"


def run(*args: str) -> int:
    result = subprocess.run(args, cwd=ROOT)
    return result.returncode


def main() -> int:
    claude = shutil.which("claude")
    if claude is None:
        print("Fleetcraft validation requires the Claude Code CLI on PATH.", file=sys.stderr)
        return 2
    if run(claude, "plugin", "validate", str(ROOT), "--strict") != 0:
        return 1
    return run(claude, "plugin", "validate", str(PLUGIN_ROOT), "--strict")


if __name__ == "__main__":
    raise SystemExit(main())

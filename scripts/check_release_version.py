#!/usr/bin/env python3
"""Bind a release tag to the repository and generated-plugin version."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def project_version(path: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ValueError("pyproject.toml has no project version")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag", default=os.environ.get("FLEETCRAFT_TAG", ""))
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        plugin = json.loads((root / "plugins" / "fleetcraft" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        version = plugin["version"]
        values = {"tag": args.tag, "plugin": version, "marketplace": marketplace["metadata"]["version"], "project": project_version(root / "pyproject.toml")}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"release version check: invalid metadata: {exc}", file=sys.stderr)
        return 2
    if values["tag"] != "v" + version or any(values[name] != version for name in ("marketplace", "project")):
        print("release version check: mismatch " + " ".join(f"{key}={value}" for key, value in values.items()), file=sys.stderr)
        return 1
    print(f"release version check: OK tag={args.tag} version={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

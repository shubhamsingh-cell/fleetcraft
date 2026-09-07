#!/usr/bin/env python3
"""Compare the checked-in generated plugin with a fresh isolated build."""
from __future__ import annotations
import os, stat, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = Path(os.environ.get("FLEETCRAFT_PLUGIN_PARITY_PLUGIN", ROOT / "plugins" / "fleetcraft"))

def inventory(root: Path) -> tuple[dict[str, tuple[bytes, int]], set[str]]:
    files, directories = {}, set()
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink(): raise ValueError("symlink in plugin tree: " + rel)
        if path.is_dir(): directories.add(rel)
        if path.is_file(): files[rel] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    return files, directories

def main() -> int:
    if not PLUGIN.is_dir(): print("plugin parity failed: checked-in plugin missing", file=sys.stderr); return 1
    with tempfile.TemporaryDirectory(prefix="fleetcraft-parity-") as tmp:
        expected = Path(tmp) / "fleetcraft"
        env = {**os.environ, "FLEETCRAFT_PLUGIN_DEST": str(expected)}
        run = subprocess.run([sys.executable, "scripts/build_plugin.py"], cwd=ROOT, env=env, text=True, capture_output=True)
        if run.returncode: print("plugin parity failed: isolated build failed\n" + run.stderr, file=sys.stderr); return 1
        try: (actual, actual_dirs), (wanted, wanted_dirs) = inventory(PLUGIN), inventory(expected)
        except ValueError as exc: print("plugin parity failed: " + str(exc), file=sys.stderr); return 1
    missing, extra = sorted(set(wanted)-set(actual)), sorted(set(actual)-set(wanted))
    changed = sorted(name for name in set(actual)&set(wanted) if actual[name] != wanted[name])
    missing_dirs, extra_dirs = sorted(wanted_dirs-actual_dirs), sorted(actual_dirs-wanted_dirs)
    if missing or extra or changed or missing_dirs or extra_dirs:
        parts = (["missing=" + ",".join(missing)] if missing else []) + (["extra=" + ",".join(extra)] if extra else []) + (["changed=" + ",".join(changed)] if changed else []) + (["missing_dirs=" + ",".join(missing_dirs)] if missing_dirs else []) + (["extra_dirs=" + ",".join(extra_dirs)] if extra_dirs else [])
        print("plugin parity failed: " + " ".join(parts), file=sys.stderr); return 1
    print("plugin parity: OK")
    return 0

if __name__ == "__main__": raise SystemExit(main())

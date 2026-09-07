#!/usr/bin/env python3
"""Reconstruct and prove Fleetcraft strict-parser regressions.

The saved sources are an immutable pre-fix baseline. This script derives a
candidate-to-baseline patch, verifies it with Git, reconstructs the baseline in
an isolated copy, byte-compares every target, then runs the same unchanged test
module on both baseline and candidate. Its artifact is deterministic: paths
are normalized and no wall-clock timestamp is recorded.
"""

from __future__ import annotations

import difflib
import hashlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "plugins" / "fleetcraft" / "hooks"
SNAPSHOTS = ROOT / "artifacts" / "strict-parser-pre-fix-source"
PATCH = ROOT / "artifacts" / "strict-parser-pre-fix.reverse.patch"
ARTIFACT = ROOT / "artifacts" / "strict-parser-regressions.txt"
TARGET = "tests.test_strict_parser_regressions"
SOURCE_NAMES = (
    "fleet_hook_utils.py",
    "fleet-delegation-guard.py",
    "autoload-judgment.py",
    "completion-gate.py",
)
# The pre-fix fixture must fail only these named assertions. Any ERROR, import
# failure, or extra/missing failure is evidence corruption, not a pass.
EXPECTED_PRE_FIX_FAILURES = {
    "test_git_push_set_upstream_flags_preserve_genuine_dry_runs",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_hook(name: str) -> str:
    return f"plugins/fleetcraft/hooks/{name}"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def candidate_to_snapshot_patch() -> str:
    """Create a portable reverse patch from candidate sources to snapshots."""
    chunks: list[str] = []
    for name in SOURCE_NAMES:
        candidate = (HOOKS / name).read_text(encoding="utf-8").splitlines(keepends=True)
        baseline = (SNAPSHOTS / name).read_text(encoding="utf-8").splitlines(keepends=True)
        diff = difflib.unified_diff(
            candidate, baseline, fromfile=f"a/{relative_hook(name)}",
            tofile=f"b/{relative_hook(name)}", lineterm="",
        )
        chunks.extend(line if line.endswith("\n") else line + "\n" for line in diff)
    return "".join(chunks)


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True)


def normalizer(temporary: Path):
    replacements = (
        (str(ROOT), "<REPO>"),
        (str(sys.executable), "<PYTHON>"),
        (str(temporary), "<TEMP>"),
    )

    def normalize(value: str) -> str:
        for before, after in replacements:
            value = value.replace(before, after)
        value = re.sub(r"/(?:private/)?var/folders/[^\s'\"]+", "<TEMP>", value)
        value = re.sub(
            r"/Library/Developer/CommandLineTools/Library/Frameworks/Python3\.framework/Versions/[0-9.]+/lib/python[0-9.]+",
            "<PYTHON>", value,
        )
        return re.sub(r"Ran ([0-9]+ tests) in [0-9.]+s", r"Ran \1 in <DURATION>", value)

    return normalize


def record(label: str, result: subprocess.CompletedProcess[str], normalize) -> str:
    return "\n".join((
        f"## {label}", f"exit: {result.returncode}", "stdout:",
        normalize(result.stdout) if result.stdout else "<empty>", "stderr:",
        normalize(result.stderr) if result.stderr else "<empty>", "",
    ))


def named_failures(stderr: str) -> set[str]:
    return set(re.findall(r"^FAIL: (test_[A-Za-z0-9_]+) ", stderr, flags=re.MULTILINE))


def has_unexpected_test_failure(stderr: str) -> bool:
    return bool(re.search(r"^(?:ERROR|UNEXPECTED SUCCESS): ", stderr, flags=re.MULTILINE))


def all_byte_matches(results: list[bool]) -> bool:
    """Keep verification bound to comparison booleans, never display labels."""
    return bool(results) and all(results)


def main() -> int:
    test_command = [sys.executable, "-m", "unittest", TARGET, "-v"]
    patch_text = candidate_to_snapshot_patch()
    PATCH.write_text(patch_text, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="fleetcraft-strict-regression-") as temporary_text:
        temporary = Path(temporary_text)
        normalize = normalizer(temporary)
        candidate_tree = temporary / "candidate"
        reconstructed_tree = temporary / "reconstructed"
        ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "node_modules")
        shutil.copytree(ROOT, candidate_tree, ignore=ignore)
        shutil.copytree(ROOT, reconstructed_tree, ignore=ignore)
        patch_file = reconstructed_tree / "strict-parser-pre-fix.reverse.patch"
        patch_file.write_text(patch_text, encoding="utf-8")
        check = run(["git", "apply", "--check", str(patch_file)], reconstructed_tree)
        apply = run(["git", "apply", str(patch_file)], reconstructed_tree)
        byte_checks: list[str] = []
        byte_results: list[bool] = []
        for name in SOURCE_NAMES:
            reconstructed = reconstructed_tree / relative_hook(name)
            snapshot = SNAPSHOTS / name
            matched = reconstructed.read_bytes() == snapshot.read_bytes()
            byte_results.append(matched)
            byte_checks.append(f"{relative_hook(name)}: {'MATCH' if matched else 'MISMATCH'}")
        test_before = digest(candidate_tree / "tests" / "test_strict_parser_regressions.py")
        baseline = run(test_command, reconstructed_tree)
        candidate = run(test_command, candidate_tree)
        test_after = digest(candidate_tree / "tests" / "test_strict_parser_regressions.py")
        baseline_failures = named_failures(baseline.stderr)
        reconstructed_matches = all_byte_matches(byte_results)
        verified = (
            check.returncode == 0 and apply.returncode == 0 and reconstructed_matches
            and test_before == test_after and baseline.returncode != 0
            and baseline_failures == EXPECTED_PRE_FIX_FAILURES
            and not has_unexpected_test_failure(baseline.stderr)
            and candidate.returncode == 0 and not has_unexpected_test_failure(candidate.stderr)
        )
        input_paths = [SNAPSHOTS / name for name in SOURCE_NAMES] + [HOOKS / name for name in SOURCE_NAMES] + [ROOT / "tests" / "test_strict_parser_regressions.py", PATCH]
        content = [
            "Fleetcraft strict parser reproducibility evidence",
            "format: deterministic; no capture timestamp is recorded",
            "repository: <REPO>",
            f"interpreter: <PYTHON> ({platform.python_version()})",
            f"platform: {platform.platform()}",
            f"test_command: <PYTHON> -m unittest {TARGET} -v", "",
            "## SHA-256 inputs",
            *(f"{digest(path)}  {display_path(path)}" for path in input_paths), "",
            "## reconstruction byte comparisons", *byte_checks,
            f"targeted_test_unchanged: {'MATCH' if test_before == test_after else 'MISMATCH'}", "",
            "## expected pre-fix assertion failures", *sorted(EXPECTED_PRE_FIX_FAILURES), "",
            record("git apply --check candidate-to-pre-fix patch", check, normalize),
            record("git apply candidate-to-pre-fix patch", apply, normalize),
            record("reconstructed pre-fix targeted tests", baseline, normalize),
            record("current candidate targeted tests", candidate, normalize),
            f"verification: {'PASS' if verified else 'FAIL'}", "",
        ]
        ARTIFACT.write_text("\n".join(content), encoding="utf-8")
    print(ARTIFACT)
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())

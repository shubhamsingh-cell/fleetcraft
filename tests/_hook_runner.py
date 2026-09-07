"""Shared subprocess-invocation infrastructure for tests/test_hooks.py.

Not a test module itself (leading underscore keeps both `unittest discover`
and `pytest`'s default `test_*.py` / `*_test.py` collection patterns from
picking it up). Everything here exists to make every hook invocation in the
suite:

  1. a REAL subprocess call (`python3 <hook>.py` with JSON on stdin), exactly
     how Claude Code itself invokes a hook -- never an `import` of the hook
     module, so we are testing the actual CLI contract;
  2. time-bounded, so a hung hook fails the test instead of hanging the
     suite (or CI) forever;
  3. filesystem-isolated by default -- HOME and TMPDIR point at a fresh
     `tempfile.TemporaryDirectory` per test, so nothing here can read or
     write the real `~/.claude`, the real `/tmp/claude-tool-routing-guard`,
     or the real `fable-judgment` skill unless a test deliberately opts a
     hook into a controlled fake HOME it built itself.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks"
TIMEOUT = 5  # seconds -- generous for a hook that should do a few regex scans

HOOK_FILES = {
    "autoload_judgment": "autoload-judgment.py",
    "fleet_delegation_guard": "fleet-delegation-guard.py",
    "skill_routing_guard": "skill-routing-guard.py",
    "tool_routing_guard": "tool-routing-guard.py",
    "retrieval_honesty_guard": "retrieval-honesty-guard.py",
}

for _key, _fname in HOOK_FILES.items():
    _path = HOOKS_DIR / _fname
    if not _path.is_file():
        raise RuntimeError(
            f"tests/_hook_runner.py: expected hook file missing: {_path} "
            f"(HOOKS_DIR resolved to {HOOKS_DIR}) -- did the hooks/ layout change?"
        )


def run_hook_subprocess(hook_key, stdin_text, env, timeout=TIMEOUT):
    """Invoke hooks/<HOOK_FILES[hook_key]> as a subprocess, feeding
    `stdin_text` on stdin exactly as the Claude Code harness would. Returns
    the completed subprocess.CompletedProcess (never raises on a non-zero
    exit -- callers assert on `.returncode` themselves so a crash is a test
    FAILURE with a clear message, not a Python traceback from this helper).
    """
    path = HOOKS_DIR / HOOK_FILES[hook_key]
    return subprocess.run(
        [sys.executable, str(path)],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


class IsolatedHookTestCase(unittest.TestCase):
    """Base class for every hook TestCase in test_hooks.py.

    setUp() creates a fresh temp directory tree per test and points HOME /
    TMPDIR at it. Individual test methods may layer additional env vars on
    top via `env_overrides` (e.g. CLAUDE_TOOL_ROUTING_STATE_DIR) but should
    never point a hook at the real ~/.claude or the real system temp dir.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory(prefix="fleetcraft-hooktest-")
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_root = Path(self._tmpdir.name)
        self.home = self.tmp_root / "home"
        self.tmp = self.tmp_root / "tmp"
        self.home.mkdir()
        self.tmp.mkdir()

    # -- environment ---------------------------------------------------
    def base_env(self, **overrides):
        env = {
            "HOME": str(self.home),
            "TMPDIR": str(self.tmp),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }
        env.update(overrides)
        return env

    def run_hook(self, hook_key, stdin_text, env_overrides=None, timeout=TIMEOUT):
        env = self.base_env(**(env_overrides or {}))
        return run_hook_subprocess(hook_key, stdin_text, env=env, timeout=timeout)

    def run_hook_json(self, hook_key, payload, env_overrides=None, timeout=TIMEOUT):
        """Convenience: json.dumps(payload) -> stdin."""
        return self.run_hook(hook_key, json.dumps(payload), env_overrides, timeout)

    # -- assertions ------------------------------------------------------
    def assert_exit0(self, proc, msg=""):
        self.assertEqual(
            proc.returncode, 0,
            f"expected exit 0, got {proc.returncode}. {msg}\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}",
        )

    def assert_silent(self, proc, msg=""):
        """No decision, no injected context: exit 0 and empty stdout."""
        self.assert_exit0(proc, msg)
        self.assertEqual(
            proc.stdout.strip(), "",
            f"expected silence (no stdout) but got: {proc.stdout!r}. {msg}",
        )

    def assert_fires(self, proc, contains=None, msg=""):
        """Exit 0 with a non-empty, JSON-parseable hookSpecificOutput.
        Returns the parsed payload so callers can inspect further fields
        (permissionDecision, additionalContext, etc). If `contains` is
        given, asserts that substring appears in additionalContext."""
        self.assert_exit0(proc, msg)
        stripped = proc.stdout.strip()
        self.assertTrue(stripped, f"expected non-empty stdout JSON. {msg}")
        data = json.loads(stripped)
        self.assertIn("hookSpecificOutput", data, f"payload={data!r}. {msg}")
        if contains is not None:
            ctx = data["hookSpecificOutput"].get("additionalContext", "")
            self.assertIn(contains, ctx, f"additionalContext={ctx!r}. {msg}")
        return data

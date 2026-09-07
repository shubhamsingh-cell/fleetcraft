"""Focused strict-mode regression contract.

These are intentionally separate from broad runtime unit coverage: the reproducibility
script runs this same module against immutable pre-fix sources and the candidate.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "plugins" / "fleetcraft" / "hooks"


def invoke(script: str, payload: object, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    result = subprocess.run(
        [sys.executable, str(HOOKS / script)], input=json.dumps(payload), text=True,
        capture_output=True, cwd=HOOKS, env=process_env,
    )
    return result.returncode, result.stdout, result.stderr


def invoke_raw(script: str, raw_payload: str, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    """Invoke a hook with deliberately malformed stdin for parser contracts."""
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    result = subprocess.run(
        [sys.executable, str(HOOKS / script)], input=raw_payload, text=True,
        capture_output=True, cwd=HOOKS, env=process_env,
    )
    return result.returncode, result.stdout, result.stderr


class StrictParserRegressions(unittest.TestCase):
    strict = {"CLAUDE_PLUGIN_OPTION_DELEGATION_MODE": "strict"}

    def parse_output(self, stdout: str, command: str) -> dict[str, object]:
        try:
            value = json.loads(stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"hook did not emit one JSON object for {command!r}: {exc}")
        self.assertIsInstance(value, dict, command)
        return value

    def assert_asks(self, command: str) -> None:
        _, stdout, stderr = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}}, self.strict)
        self.assertEqual(stderr, "", command)
        output = self.parse_output(stdout, command)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask", command)

    def test_unknown_shell_syntax_fails_closed(self) -> None:
        for command in (
            "echo one\ngit push origin main", "publish() { git push origin main; }; publish",
            "function publish { git push origin main; }; publish", "( git push origin main )",
            "{ git push origin main; }", "if true; then git push origin main; fi",
            "case x in x) git push origin main;; esac", "eval '$PUBLISH'", "$PUBLISH origin main",
            "env -S 'git push origin main'", "/usr/bin/time -f '%e' git push origin main",
        ):
            self.assert_asks(command)

    def test_git_help_and_dry_run_only_apply_before_double_dash(self) -> None:
        for command in ("git commit -m release -- --help", "git push origin -- -n"):
            self.assert_asks(command)
        for command in ("git push --help", "git push --dry-run origin", "git -C /tmp push -n origin"):
            _, stdout, stderr = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}}, self.strict)
            self.assertEqual((stdout, stderr), ("", ""), command)

    def test_git_option_values_are_not_help_or_dry_run_exemptions(self) -> None:
        for command in (
            "git commit -m --help --allow-empty",
            "git push -o --dry-run origin main",
            "git push --push-option --help origin main",
        ):
            self.assert_asks(command)

    def test_git_push_set_upstream_flags_preserve_genuine_dry_runs(self) -> None:
        for command in (
            "git push -u --dry-run origin main",
            "git push --set-upstream -n origin main",
        ):
            _, stdout, stderr = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}}, self.strict)
            self.assertEqual((stdout, stderr), ("", ""), command)

    def test_boolean_options_fail_safe(self) -> None:
        _, stdout, stderr = invoke("autoload-judgment.py", {"session_id": "test"}, {"CLAUDE_PLUGIN_OPTION_AUTOLOAD_JUDGMENT": "perhaps"})
        self.assertEqual(stderr, "")
        self.assertIn("systemMessage", stdout)
        self.assertIn("judgment kernel", stdout)
        verified = {"task_description": "[fleetcraft:verified]"}
        code, _, stderr = invoke("completion-gate.py", verified, {"CLAUDE_PLUGIN_OPTION_COMPLETION_GATE": "perhaps"})
        self.assertEqual(code, 2)
        self.assertIn("invalid", stderr.lower())

    def test_parent_git_config_push_is_guarded(self) -> None:
        self.assert_asks("git -c user.name=example push origin main")

    def test_dynamic_executable_control_tokens_fail_closed(self) -> None:
        for command in (
            'ACTION=push; git "$ACTION" origin main',
            'MODE=-c; bash "$MODE" "git push origin main"',
        ):
            self.assert_asks(command)

    def test_lexer_failures_fail_closed(self) -> None:
        for command in ("git push '", "git push \\"):
            self.assert_asks(command)

    def test_malformed_payload_contracts_are_single_json_objects(self) -> None:
        code, stdout, stderr = invoke_raw("fleet-delegation-guard.py", "{", self.strict)
        self.assertEqual((code, stderr), (0, ""))
        strict = self.parse_output(stdout, "strict malformed JSON")
        self.assertEqual(strict["hookSpecificOutput"]["permissionDecision"], "ask")

        code, stdout, stderr = invoke_raw("fleet-delegation-guard.py", "{")
        self.assertEqual((code, stderr), (0, ""))
        audit = self.parse_output(stdout, "audit malformed JSON")
        self.assertIn("Audit mode does not block", audit["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("permissionDecision", audit["hookSpecificOutput"])

    def test_invalid_autoload_is_one_parseable_object_with_warning_and_context(self) -> None:
        code, stdout, stderr = invoke(
            "autoload-judgment.py", {"session_id": "test"},
            {"CLAUDE_PLUGIN_OPTION_AUTOLOAD_JUDGMENT": "perhaps"},
        )
        self.assertEqual((code, stderr), (0, ""))
        output = self.parse_output(stdout, "invalid autoload configuration")
        self.assertIn("invalid", output["systemMessage"].lower())
        self.assertIn("judgment kernel", output["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()

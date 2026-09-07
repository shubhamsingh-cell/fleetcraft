from __future__ import annotations

import json
import importlib.util
import io
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "fleetcraft"
HOOKS = PLUGIN_ROOT / "hooks"


def invoke(script: str, payload: object, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    result = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=HOOKS,
        env=process_env,
    )
    return result.returncode, result.stdout, result.stderr


def load_hook(module_name: str, script: str):
    sys.path.insert(0, str(HOOKS))
    try:
        spec = importlib.util.spec_from_file_location(module_name, HOOKS / script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class PluginRuntimeTests(unittest.TestCase):
    def test_manifest_and_wiring_are_hermetic(self) -> None:
        manifest = json.loads((PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text())
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        wiring = json.loads((HOOKS / "hooks.json").read_text())
        self.assertEqual(manifest["name"], "fleetcraft")
        self.assertEqual(manifest["version"], "0.1.1")
        self.assertEqual(manifest["userConfig"]["delegation_mode"]["type"], "string")
        self.assertNotIn("enum", manifest["userConfig"]["delegation_mode"])
        self.assertNotIn("hooks", manifest)
        self.assertEqual(marketplace["plugins"][0]["source"], "./plugins/fleetcraft")
        self.assertIn("PreToolUse", wiring["hooks"])
        self.assertIn("PostToolUse", wiring["hooks"])
        serialized = json.dumps(wiring)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", serialized)
        self.assertNotIn("~/.claude", serialized)
        for groups in wiring["hooks"].values():
            for group in groups:
                for handler in group["hooks"]:
                    self.assertEqual(handler["command"], "python3")
                    self.assertTrue(handler["args"])
                    self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", handler["command"])
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (PLUGIN_ROOT / "LICENSE").read_bytes())
        self.assertEqual(
            (ROOT / "THIRD_PARTY_NOTICES.md").read_bytes(),
            (PLUGIN_ROOT / "THIRD_PARTY_NOTICES.md").read_bytes(),
        )
        self.assertFalse((PLUGIN_ROOT / ".github").exists())
        self.assertFalse((PLUGIN_ROOT / "tests").exists())
        self.assertFalse((PLUGIN_ROOT / "artifacts").exists())
        self.assertFalse((PLUGIN_ROOT / "pyproject.toml").exists())

    def test_autoload_uses_bundled_kernel_under_limit(self) -> None:
        code, stdout, stderr = invoke("autoload-judgment.py", {"session_id": "clean"})
        self.assertEqual((code, stderr), (0, ""))
        output = json.loads(stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Fleetcraft judgment kernel", context)
        self.assertLess(len(context), 10_000)

    def test_autoload_can_be_disabled_with_plugin_option(self) -> None:
        _, stdout, _ = invoke("autoload-judgment.py", {"session_id": "disabled"}, {"CLAUDE_PLUGIN_OPTION_AUTOLOAD_JUDGMENT": "false"})
        self.assertEqual(stdout, "")

    def test_autoload_corruption_is_visible(self) -> None:
        module = load_hook("fleetcraft_autoload", "autoload-judgment.py")
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(output):
            module.emit_kernel(Path(temporary) / "missing.md")
        self.assertIn("systemMessage", output.getvalue())
        self.assertIn("did not load", output.getvalue())

    def test_autoload_normalizes_kernel_bom_crlf_and_enforces_exact_boundary(self) -> None:
        module = load_hook("fleetcraft_autoload_boundary", "autoload-judgment.py")
        prefix = "Fleetcraft judgment kernel (SessionStart runtime):\n\n"
        with tempfile.TemporaryDirectory() as temporary:
            kernel = Path(temporary) / "kernel.md"
            kernel.write_bytes(b"\xef\xbb\xbfline one\r\nline two\r\n")
            context = module.kernel_context(kernel)
            self.assertNotIn("\ufeff", context)
            self.assertNotIn("\r", context)
            self.assertIn("line one\nline two", context)
            kernel.write_text("x" * (module.MAX_CONTEXT_CHARS - len(prefix)), encoding="utf-8")
            self.assertEqual(len(module.kernel_context(kernel)), module.MAX_CONTEXT_CHARS)
            kernel.write_text("x" * (module.MAX_CONTEXT_CHARS - len(prefix) + 1), encoding="utf-8")
            with self.assertRaises(ValueError):
                module.kernel_context(kernel)

    def test_delegation_strict_confirms_matching_actions_for_main_and_delegated_agents(self) -> None:
        payload = {"tool_input": {"command": "git -C '/tmp/a b' push origin main"}}
        _, audit, _ = invoke("fleet-delegation-guard.py", payload)
        self.assertNotIn("permissionDecision", audit)
        _, strict, _ = invoke("fleet-delegation-guard.py", payload, {"CLAUDE_PLUGIN_OPTION_DELEGATION_MODE": "strict"})
        self.assertEqual(json.loads(strict)["hookSpecificOutput"]["permissionDecision"], "ask")
        payload["agent_id"] = "agent-1"
        _, strict_agent, _ = invoke("fleet-delegation-guard.py", payload, {"CLAUDE_PLUGIN_OPTION_DELEGATION_MODE": "strict"})
        self.assertEqual(json.loads(strict_agent)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_delegation_ignores_echo_and_handles_malformed_payload(self) -> None:
        _, stdout, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": "echo 'git push origin main'"}})
        self.assertEqual(stdout, "")
        result = subprocess.run([sys.executable, str(HOOKS / "fleet-delegation-guard.py")], input="{", text=True, capture_output=True, cwd=HOOKS)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        output = json.loads(result.stdout)
        self.assertIn("Audit mode does not block", output["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("permissionDecision", output["hookSpecificOutput"])

    def test_delegation_handles_gh_options_and_compound_commands(self) -> None:
        commands = (
            "gh pr --repo acme/repo create --title release",
            "gh --repo acme/repo pr merge 42",
            "pytest -q && git --no-optional-locks push origin main",
            "bash -lc 'git push origin main'",
            "pwsh -Command 'gh release create v1.2.3'",
        )
        for command in commands:
            _, stdout, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}})
            self.assertTrue(stdout, command)

    def test_delegation_handles_wrapped_publish_commands_without_status_false_positives(self) -> None:
        for command in (
            "/usr/bin/git push origin main",
            "command -- git push origin main",
            "env -- git push origin main",
            "sudo -u root git push origin main",
            "sudo --user root git push origin main",
            "sudo --user=root git push origin main",
            "sudo -uroot git push origin main",
            "bash -c -- 'git push origin main'",
            "bash -ec 'git push origin main'",
            "bash --noprofile -c 'git push origin main'",
            "sh -c 'git push origin main'",
            "echo $(git push origin main)",
            "PUBLISH=$(git push origin main)",
            "echo `git push origin main`",
        ):
            _, stdout, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}})
            self.assertIn("git push", stdout, command)
        for command in (
            "vercel --help",
            "fly status",
            "netlify status",
            "git push --dry-run",
            "git push --help",
            "git push --version",
        ):
            _, stdout, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}})
            self.assertEqual(stdout, "", command)
        for command in (
            "echo 'git push origin main'",
            "PUBLISH='$(git push origin main)'",
            "PUBLISH='`git push origin main`'",
            "echo harmless # $(git push origin main)",
            "echo '# $(git push origin main)'",
        ):
            _, stdout, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}})
            self.assertEqual(stdout, "", command)
        _, deployment, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": "vercel --prod"}})
        self.assertIn("vercel deploy", deployment)

    def test_delegation_adversarial_shell_forms_and_git_commit_options(self) -> None:
        guarded = (
            "git commit -n -m release",
            "git commit --no-verify -m release",
            "env -S 'git push origin main'",
            "{ git push origin main; }",
            "( git push origin main )",
            "if true; then git push origin main; fi",
            "sudo -D /tmp -R /tmp -T 5 git push origin main",
            "echo $(echo $(echo $(git push origin main)))",
        )
        for command in guarded:
            _, stdout, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}})
            self.assertIn("git ", stdout, command)
        for command in (
            "git push -n origin main",
            "git push --dry-run origin main",
            "echo 'env -S \"git push\"'",
            "# { git push origin main; }\necho safe",
        ):
            _, stdout, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": command}})
            self.assertEqual(stdout, "", command)

    def test_hooks_tolerate_malformed_payload_shapes(self) -> None:
        scripts = (
            "autoload-judgment.py",
            "agent-telemetry.py",
            "fleet-delegation-guard.py",
            "skill-routing-guard.py",
            "completion-gate.py",
            "evidence-batch.py",
        )
        payloads: tuple[object, ...] = (None, [], 3, "text", {"tool_input": []}, {"tool_input": {"command": 9}}, {"prompt": 7})
        for script in scripts:
            for payload in payloads:
                code, _, stderr = invoke(script, payload)
                self.assertEqual((code, stderr), (0, ""), (script, payload))
        for payload in ({"tool_input": []}, {"tool_input": {"command": 9}}):
            _, stdout, stderr = invoke("fleet-delegation-guard.py", payload, {"CLAUDE_PLUGIN_OPTION_DELEGATION_MODE": "strict"})
            self.assertEqual(stderr, "")
            self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "ask")
        _, invalid, _ = invoke("fleet-delegation-guard.py", {"tool_input": {"command": "echo safe"}}, {"CLAUDE_PLUGIN_OPTION_DELEGATION_MODE": "danger"})
        self.assertEqual(json.loads(invalid)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_routing_positive_and_negative_corpus(self) -> None:
        positives = {
            "analyze data.csv using this SQL snippet": "tabular-analysis",
            "import data.csv and analyze duplicate rows": "tabular-analysis",
            "extract the text from brief.docx": "document-extraction",
            "email this to the client": "share-preflight",
            "publish this publicly": "share-preflight",
            "is this landing page ready to ship?": "design-ship-check",
            "draft a note to the CEO": "executive-register",
        }
        for prompt, category in positives.items():
            _, stdout, _ = invoke("skill-routing-guard.py", {"prompt": prompt})
            self.assertIn(category, stdout, prompt)
        for prompt in ("show me the data model", "send me a local reminder", "read app.py", "echo git push"):
            _, stdout, _ = invoke("skill-routing-guard.py", {"prompt": prompt})
            self.assertEqual(stdout, "", prompt)

    def test_routing_supports_upload_and_windows_file_reference(self) -> None:
        _, stdout, _ = invoke("skill-routing-guard.py", {"prompt": "Upload this export to the client after checking for API keys"})
        self.assertIn("share-preflight", stdout)
        _, document, _ = invoke("skill-routing-guard.py", {"prompt": r"Extract C:\docs\brief.docx"})
        self.assertIn("Office or mail", document)

    def test_completion_gate_requires_explicit_evidence_manifest(self) -> None:
        enabled = {"CLAUDE_PLUGIN_OPTION_COMPLETION_GATE": "true"}
        payload = {"task_subject": "Release", "task_description": "[fleetcraft:verified]"}
        code, _, stderr = invoke("completion-gate.py", payload, enabled)
        self.assertEqual(code, 2)
        self.assertIn("Evidence:", stderr)
        valid = "[fleetcraft:verified]\nEvidence: artifact=artifacts/runtime.log; sha256=" + "a" * 64 + "\nValidation: command=python3 -m unittest; result=pass"
        code, _, stderr = invoke("completion-gate.py", {"task_description": valid}, enabled)
        self.assertEqual((code, stderr), (0, ""))
        for description in (
            "[fleetcraft:verified]\nEvidence: \nValidation: clean install",
            "[fleetcraft:verified]\nEvidence: test output\nValidation:\n",
            "[fleetcraft:verified]\nEvidence: TODO\nValidation: command=pytest; result=pass",
            "[fleetcraft:verified]\nEvidence: artifact=log; sha256=" + "a" * 64 + "\nValidation: command=pytest; result=pass",
            "[fleetcraft:verified]\nEvidence: artifact=artifacts/runtime.log; sha256=" + "a" * 64 + "\nValidation: command=x; result=pass",
            "[fleetcraft:verified]\nEvidence: artifact=log; sha256=" + "a" * 64 + "\nValidation: command=pytest; result=TODO",
            "[fleetcraft:verified]\nEvidence: artifact=artifacts/runtime.log; sha256=" + "A" * 64 + "\nValidation: command=pytest; result=pass",
        ):
            code, _, stderr = invoke("completion-gate.py", {"task_description": description}, enabled)
            self.assertEqual(code, 2)
            self.assertIn("OPEN", stderr)

    def test_batch_evidence_is_opt_in_and_does_not_parse_results(self) -> None:
        payload = {"tool_calls": [{"tool_name": "Agent", "tool_response": "serialized result containing claude-sonnet-5"}]}
        _, disabled, _ = invoke("evidence-batch.py", payload)
        self.assertEqual(disabled, "")
        _, stdout, _ = invoke("evidence-batch.py", payload, {"CLAUDE_PLUGIN_OPTION_EVIDENCE_BATCH": "true"})
        self.assertIn("Agent", stdout)
        self.assertNotIn("claude-sonnet-5", stdout)

    def test_agent_post_tool_hook_reports_runtime_telemetry(self) -> None:
        payload = {"tool_response": {"resolvedModel": "claude-sonnet-5", "modelsUsed": ["claude-sonnet-5", "claude-haiku-4-5"]}}
        _, stdout, _ = invoke("agent-telemetry.py", payload)
        self.assertIn("claude-sonnet-5", stdout)
        self.assertIn("claude-haiku-4-5", stdout)

    def test_direct_hook_scripts_are_executable(self) -> None:
        for script in ("autoload-judgment.py", "agent-telemetry.py", "fleet-delegation-guard.py", "skill-routing-guard.py", "completion-gate.py", "evidence-batch.py"):
            self.assertTrue((HOOKS / script).stat().st_mode & stat.S_IXUSR, script)

    def test_clean_plugin_directory_can_run_without_home_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            code, stdout, _ = invoke("autoload-judgment.py", {"session_id": "clean"}, {"HOME": str(home)})
            self.assertEqual(code, 0)
            self.assertIn("Fleetcraft judgment kernel", stdout)

    def test_internal_markdown_links_resolve(self) -> None:
        link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        missing: list[str] = []
        for document in ROOT.rglob("*.md"):
            for target in link.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                path = target.split("#", 1)[0]
                if path and not (document.parent / path).resolve().exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])

    def test_public_claim_and_plugin_invocation_contract(self) -> None:
        """Current-policy invariant coverage, not failing-before regression evidence."""
        operational = [
            path
            for path in ROOT.rglob("*.md")
            if path.name not in {"THIRD_PARTY_NOTICES.md", "LICENSE"}
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in operational)
        for stale in (
            "matches or beats Fable",
            "fraction of the tokens",
            "replaces a senior design eye",
            "fable-judgment",
            "being added in this release",
            "npx-only, never installed",
        ):
            self.assertNotIn(stale, text)
        for unscoped in ("`/design-judge`", "`/growth-web-architect`"):
            self.assertNotIn(unscoped, text)
        checklist = (PLUGIN_ROOT / "skills/design-judge/references/ai-slop-checklist.md").read_text()
        self.assertIn("24 CSS px normal weight", checklist)
        self.assertIn("18.5 CSS px bold", checklist)

    def test_ci_runs_validation_and_runtime_checks(self) -> None:
        workflow = (ROOT / ".github/workflows/verify.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/selftest-guards.py", workflow)
        self.assertIn("python3 scripts/validate-plugin.py", workflow)
        self.assertIn("python3 scripts/clean-install-smoke.py", workflow)
        self.assertIn("${{ runner.temp }}", workflow)
        self.assertIn("concurrency:", workflow)
        self.assertIn("tags: ['v*']", workflow)
        self.assertIn("git archive", workflow)


if __name__ == "__main__":
    unittest.main()

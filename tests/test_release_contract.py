from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, tempfile, unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "fleetcraft"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

class ReleaseContractTests(unittest.TestCase):
    def build(self, destination: Path):
        return subprocess.run(
            [sys.executable, "scripts/build_plugin.py"], cwd=ROOT,
            env={**os.environ, "FLEETCRAFT_PLUGIN_DEST": str(destination)},
            text=True, capture_output=True,
        )

    def test_builder_refuses_preexisting_or_unsafe_destinations(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "existing"; existing.mkdir()
            sentinel = existing / "sentinel.txt"; sentinel.write_text("keep", encoding="utf-8")
            result = self.build(existing)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(sentinel.is_file())
            self.assertIn("fresh and non-existent", result.stderr)
            self.assertNotEqual(self.build(ROOT).returncode, 0)
            link = Path(tmp) / "link"; link.symlink_to(Path(tmp) / "target")
            self.assertNotEqual(self.build(link).returncode, 0)
            fresh = Path(tmp) / "fresh"
            self.assertEqual(self.build(fresh).returncode, 0)
            self.assertTrue((fresh / ".claude-plugin" / "plugin.json").is_file())
            self.assertNotEqual(self.build(ROOT / "new-external-destination").returncode, 0)

    def test_builder_refuses_canonical_parent_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "repo"
            shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns(".git", "plugins", "__pycache__", "*.pyc"))
            external = Path(tmp) / "external"; (external / "fleetcraft").mkdir(parents=True)
            sentinel = external / "fleetcraft" / "sentinel.txt"; sentinel.write_text("keep", encoding="utf-8")
            (copied / "plugins").symlink_to(external, target_is_directory=True)
            result = subprocess.run([sys.executable, "scripts/build_plugin.py"], cwd=copied, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(sentinel.is_file())
            self.assertIn("beneath a symlink", result.stderr)

    def test_builder_refuses_a_nested_symlink_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            sensitive = Path(tmp) / "sensitive"; sensitive.mkdir()
            sentinel = sensitive / "sentinel.txt"; sentinel.write_text("keep", encoding="utf-8")
            link = Path(tmp) / "link"; link.symlink_to(sensitive, target_is_directory=True)
            result = self.build(link / "nested" / "fleetcraft")
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(sentinel.is_file())
            self.assertFalse((sensitive / "nested" / "fleetcraft").exists())

    def test_autoload_warnings_never_emit_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            autoload = plugin / "hooks" / "autoload-judgment.py"
            invalid = subprocess.run([sys.executable, autoload], env={**os.environ, "CLAUDE_PLUGIN_OPTION_AUTOLOAD_JUDGMENT": "invalid"}, text=True, capture_output=True)
            invalid_output = json.loads(invalid.stdout)
            self.assertIn("systemMessage", invalid_output)
            self.assertIn("hookSpecificOutput", invalid_output)
            (plugin / "hooks" / "judgment-kernel.md").write_text("x" * 9001, encoding="utf-8")
            oversized = subprocess.run([sys.executable, autoload], text=True, capture_output=True)
            oversized_output = json.loads(oversized.stdout)
            self.assertIn("systemMessage", oversized_output)
            self.assertNotIn("hookSpecificOutput", oversized_output)

    def test_doctor_does_not_mutate_plugin_tree_with_bytecode(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            before = {path.relative_to(plugin): hashlib.sha256(path.read_bytes()).hexdigest() for path in plugin.rglob("*") if path.is_file()}
            doctor = plugin / "scripts" / "fleetcraft-doctor.py"
            result = subprocess.run([sys.executable, "-c", "import os, runpy, sys; sys.pycache_prefix = None; runpy.run_path(os.environ['DOCTOR'], run_name='__main__')"], env={**os.environ, "DOCTOR": str(doctor)}, text=True, capture_output=True)
            after = {path.relative_to(plugin): hashlib.sha256(path.read_bytes()).hexdigest() for path in plugin.rglob("*") if path.is_file()}
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(before, after)
            self.assertEqual(list(plugin.rglob("*.pyc")), [])

    def test_doctor_rejects_missing_distribution_content_and_tampered_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            doctor = plugin / "scripts" / "fleetcraft-doctor.py"
            shutil.rmtree(plugin / "skills")
            (plugin / "LICENSE").unlink()
            missing = subprocess.run([sys.executable, "-B", doctor], text=True, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("missing skills/doctor/SKILL.md", missing.stdout)
            self.assertIn("missing LICENSE", missing.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            hook = plugin / "hooks" / "fleet-delegation-guard.py"
            hook.write_text(hook.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
            tampered = subprocess.run([sys.executable, "-B", plugin / "scripts" / "fleetcraft-doctor.py"], text=True, capture_output=True)
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("modified hooks/fleet-delegation-guard.py", tampered.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            (plugin / "hooks" / "README.md").unlink()
            inventory = plugin / "scripts" / "distribution-inventory.json"
            data = json.loads(inventory.read_text(encoding="utf-8")); data["files"].pop("hooks/README.md")
            inventory.write_text(json.dumps(data), encoding="utf-8")
            missing = subprocess.run([sys.executable, "-B", plugin / "scripts" / "fleetcraft-doctor.py"], text=True, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("inventory path set", missing.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            (plugin / "extra.txt").write_text("extra", encoding="utf-8")
            extra = subprocess.run([sys.executable, "-B", plugin / "scripts" / "fleetcraft-doctor.py"], text=True, capture_output=True)
            self.assertNotEqual(extra.returncode, 0)
            self.assertIn("unexpected or missing files", extra.stdout)

    def test_doctor_and_clean_install_allow_only_an_empty_regular_in_use_directory(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("clean_install_smoke", ROOT / "scripts" / "clean_install_smoke.py")
        smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            doctor = plugin / "scripts" / "fleetcraft-doctor.py"
            marker = plugin / ".in_use"
            marker.mkdir()
            allowed = subprocess.run([sys.executable, "-B", doctor], text=True, capture_output=True)
            self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
            self.assertIsInstance(smoke.inspect_install_package(plugin), tuple)
            (marker / "nested").write_text("not empty", encoding="utf-8")
            nonempty = subprocess.run([sys.executable, "-B", doctor], text=True, capture_output=True)
            self.assertNotEqual(nonempty.returncode, 0)
            with self.assertRaisesRegex(RuntimeError, "unexpected top-level entries"):
                smoke.inspect_install_package(plugin)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO support is required")
    def test_doctor_rejects_a_top_level_fifo_without_reading_it(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("clean_install_smoke", ROOT / "scripts" / "clean_install_smoke.py")
        smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            os.mkfifo(plugin / ".in_use")
            result = subprocess.run([sys.executable, "-B", plugin / "scripts" / "fleetcraft-doctor.py"], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported filesystem entry .in_use", result.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "fleetcraft"; self.assertEqual(self.build(plugin).returncode, 0)
            marker = plugin / ".in_use"
            outside = Path(tmp) / "outside"; outside.mkdir()
            marker.symlink_to(outside, target_is_directory=True)
            rejected = subprocess.run([sys.executable, "-B", plugin / "scripts" / "fleetcraft-doctor.py"], text=True, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("symlink .in_use", rejected.stdout)
            with self.assertRaisesRegex(RuntimeError, "unexpected top-level entries"):
                smoke.inspect_install_package(plugin)

    def test_generated_manifest_wires_opt_in_runtime_hooks(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(manifest["userConfig"]["completion_gate"]["default"], False)
        self.assertEqual(manifest["userConfig"]["evidence_batch"]["default"], False)
        self.assertEqual(manifest["userConfig"]["routing_enforce"]["default"], False)
        self.assertIn("PostToolUse", hooks)
        self.assertIn("TaskCompleted", hooks)
        self.assertIn("PostToolBatch", hooks)
        self.assertTrue((PLUGIN / "hooks" / "evidence-batch.py").is_file())
        for event in hooks.values():
            for entry in event:
                for hook in entry["hooks"]:
                    self.assertEqual(hook["args"][0], "-B")

    def test_routing_plugin_option_enables_the_existing_docs_gate(self):
        payload = json.dumps({"session_id": "release-contract", "tool_name": "WebFetch", "tool_input": {"url": "https://docs.python.org/3/"}})
        with tempfile.TemporaryDirectory() as state:
            result = subprocess.run(
                [sys.executable, "hooks/tool-routing-guard.py"], cwd=ROOT, input=payload,
                env={**os.environ, "CLAUDE_PLUGIN_OPTION_ROUTING_ENFORCE": "true", "CLAUDE_TOOL_ROUTING_STATE_DIR": state},
                text=True, capture_output=True,
            )
        output = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_strict_reproducer_rejects_a_real_reconstructed_byte_mismatch(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("strict_reproducer", ROOT / "scripts" / "reproduce_strict_parser_regressions.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        original_read_bytes = Path.read_bytes
        def altered_reconstruction(path):
            value = original_read_bytes(path)
            if "/reconstructed/plugins/fleetcraft/hooks/" in str(path):
                return value + b"\n# injected comparison mismatch\n"
            return value
        with tempfile.TemporaryDirectory() as tmp:
            module.PATCH = Path(tmp) / "reverse.patch"
            module.ARTIFACT = Path(tmp) / "mismatch-report.txt"
            with patch.object(Path, "read_bytes", altered_reconstruction):
                self.assertEqual(module.main(), 1)
            report = module.ARTIFACT.read_text(encoding="utf-8")
        comparisons = [line for line in report.splitlines() if line.startswith("plugins/fleetcraft/hooks/")]
        self.assertTrue(any(line.endswith("MISMATCH") for line in comparisons))
        self.assertIn("verification: FAIL", report)
        # This is the exact pre-fix label bug: MISMATCH also ends in MATCH.
        self.assertTrue(all(line.endswith("MATCH") for line in comparisons))

    def test_generated_agents_are_namespaced_while_source_agents_are_manual(self):
        for name in ("executor.md", "verifier.md"):
            self.assertIn("- fleet-orchestrator", (ROOT / "agents" / name).read_text(encoding="utf-8"))
            self.assertIn("- fleetcraft:fleet-orchestrator", (PLUGIN / "agents" / name).read_text(encoding="utf-8"))
            self.assertIn("fleet-orchestrator` skill", (PLUGIN / "agents" / name).read_text(encoding="utf-8"))

    def test_distribution_license_notices_and_doctor_are_real(self):
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (PLUGIN / "LICENSE").read_bytes())
        self.assertEqual((ROOT / "THIRD_PARTY_NOTICES.md").read_bytes(), (PLUGIN / "THIRD_PARTY_NOTICES.md").read_bytes())
        self.assertIn('"license": "MIT AND Apache-2.0"', (PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        result = subprocess.run([sys.executable, str(PLUGIN / "scripts" / "fleetcraft-doctor.py")], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tag_workflow_anchors_and_compares_the_public_archive(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('claude plugin marketplace add "shubhamsingh-cell/fleetcraft@$FLEETCRAFT_TAG"', text)
        self.assertIn('git archive "$event_commit:plugins/fleetcraft"', text)
        self.assertIn('rmdir "$install_path/.in_use"', text)
        self.assertIn('diff -ru "$expected" "$install_path"', text)
        self.assertGreaterEqual(text.count('refs/tags/$FLEETCRAFT_TAG:refs/tags/$FLEETCRAFT_TAG'), 2)
        self.assertIn('test "$(node --version)" = "v22.22.1"', text)
        self.assertIn('test "$(npm --version)" = "10.9.4"', text)

    def test_release_version_gate_accepts_current_version_and_rejects_wrong_tag(self):
        passed = subprocess.run([sys.executable, "scripts/check_release_version.py", "--tag", "v0.3.0"], cwd=ROOT, text=True, capture_output=True)
        failed = subprocess.run([sys.executable, "scripts/check_release_version.py", "--tag", "v9.9.9"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("mismatch", failed.stderr)

if __name__ == "__main__": unittest.main()

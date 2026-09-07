from pathlib import Path
import json, os, subprocess, tempfile, unittest

ROOT = Path(__file__).parents[1]

class ManualInstallerTests(unittest.TestCase):
    def test_dry_run_with_space_path_writes_nothing_and_never_touches_settings(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft install ") as tmp:
            target = Path(tmp) / "Claude Config"
            result = subprocess.run(["bash", "scripts/install.sh", "--dry-run"], cwd=ROOT, env={**os.environ, "CLAUDE_DIR": str(target)}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("dry run", result.stdout.lower())
            self.assertFalse(target.exists())
            self.assertFalse((target / "settings.json").exists())

    def test_manual_hook_copy_includes_helper_modules(self):
        text = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        self.assertIn('HOOK_FILES=("$REPO_ROOT"/hooks/*.py)', text)
        self.assertTrue((ROOT / "hooks" / "fleet_hook_utils.py").is_file())

    def test_printed_wiring_includes_registered_optional_hooks_without_settings_write(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft install ") as tmp:
            target = Path(tmp) / "Claude Config"
            result = subprocess.run(["bash", "scripts/install.sh", "--hooks-only"], cwd=ROOT, env={**os.environ, "CLAUDE_DIR": str(target)}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('"PostToolBatch": [', result.stdout)
            self.assertIn('"TaskCompleted": [', result.stdout)
            self.assertIn('evidence-batch.py', result.stdout)
            self.assertFalse((target / "settings.json").exists())
            self.assertTrue((target / "hooks" / "evidence-batch.py").is_file())

    def test_every_printed_hook_command_executes_with_quoted_special_character_path(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft install ") as tmp:
            target = Path(tmp) / "Claude O'Connor Config"
            result = subprocess.run(["bash", "scripts/install.sh", "--hooks-only"], cwd=ROOT, env={**os.environ, "CLAUDE_DIR": str(target)}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            commands = [json.loads(line.strip().split(": ", 1)[1].rstrip(",")) for line in result.stdout.splitlines() if '"command":' in line]
            self.assertTrue(commands)
            for command in commands:
                executed = subprocess.run(["sh", "-c", command], input="{}", text=True, capture_output=True)
                self.assertEqual(executed.returncode, 0, f"{command}\n{executed.stderr}")
            self.assertFalse((target / "settings.json").exists())

if __name__ == "__main__": unittest.main()

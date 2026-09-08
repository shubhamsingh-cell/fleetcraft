from pathlib import Path
import os, shutil, subprocess, sys, tempfile, unittest

ROOT = Path(__file__).parents[1]

class PluginParityTests(unittest.TestCase):
    def test_checker_rejects_changed_extra_and_missing_generated_files(self):
        original = ROOT / "plugins" / "fleetcraft"
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "fleetcraft"; shutil.copytree(original, candidate)
            env = {**os.environ, "FLEETCRAFT_PLUGIN_PARITY_PLUGIN": str(candidate)}
            def check():
                return subprocess.run([sys.executable, "scripts/check_plugin_parity.py"], cwd=ROOT, env=env, text=True, capture_output=True)
            (candidate / "hooks" / "hooks.json").write_text("{}\n", encoding="utf-8")
            self.assertNotEqual(check().returncode, 0)
            shutil.rmtree(candidate); shutil.copytree(original, candidate)
            (candidate / "extra.txt").write_text("extra", encoding="utf-8")
            self.assertNotEqual(check().returncode, 0)
            (candidate / "extra.txt").unlink()
            (candidate / "LICENSE").unlink()
            self.assertNotEqual(check().returncode, 0)

    def test_checker_rejects_an_unexpected_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "fleetcraft"; shutil.copytree(ROOT / "plugins" / "fleetcraft", candidate)
            (candidate / "skills 2" / "duplicate").mkdir(parents=True)
            result = subprocess.run(
                [sys.executable, "scripts/check_plugin_parity.py"], cwd=ROOT,
                env={**os.environ, "FLEETCRAFT_PLUGIN_PARITY_PLUGIN": str(candidate)},
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("extra_dirs=skills 2,skills 2/duplicate", result.stderr)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO support is required")
    def test_checker_rejects_special_filesystem_entries_without_reading_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "fleetcraft"; shutil.copytree(ROOT / "plugins" / "fleetcraft", candidate)
            os.mkfifo(candidate / ".in_use")
            result = subprocess.run(
                [sys.executable, "scripts/check_plugin_parity.py"], cwd=ROOT,
                env={**os.environ, "FLEETCRAFT_PLUGIN_PARITY_PLUGIN": str(candidate)},
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported filesystem entry: .in_use", result.stderr)

if __name__ == "__main__": unittest.main()

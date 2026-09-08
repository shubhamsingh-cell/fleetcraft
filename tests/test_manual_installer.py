from pathlib import Path
import json, os, shlex, shutil, subprocess, tempfile, unittest

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

    def test_printed_wiring_matches_generated_registry_and_example(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft install ") as tmp:
            target = Path(tmp) / "Claude Config"
            result = subprocess.run(["bash", "scripts/install.sh", "--hooks-only"], cwd=ROOT, env={**os.environ, "CLAUDE_DIR": str(target)}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            event = matcher = None
            printed = set()
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if line.startswith('"') and stripped.endswith('": ['):
                    event = stripped.split('"', 2)[1]
                elif stripped.startswith('"matcher":'):
                    matcher = json.loads(stripped.split(": ", 1)[1].rstrip(","))
                elif '"command":' in stripped:
                    command = json.loads(stripped.split(": ", 1)[1].rstrip(","))
                    printed.add((event, matcher, Path(shlex.split(command)[-1]).name))
            registry = json.loads((ROOT / "plugins" / "fleetcraft" / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
            expected = {
                (event, entry.get("matcher", ""), Path(hook["args"][-1]).name)
                for event, entries in registry.items()
                for entry in entries
                for hook in entry["hooks"]
            }
            example = json.loads((ROOT / "examples" / "settings.json").read_text(encoding="utf-8"))["hooks"]
            documented = {
                (event, entry.get("matcher", ""), Path(shlex.split(hook["command"])[-1]).name)
                for event, entries in example.items()
                for entry in entries
                for hook in entry["hooks"]
            }
            self.assertEqual(printed, expected)
            self.assertEqual(documented, expected)

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

    def test_same_second_backups_preserve_each_file_and_directory_version(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft installer backup ") as tmp:
            root = Path(tmp)
            target = root / "Claude Config"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            date = bin_dir / "date"
            date.write_text("#!/bin/sh\necho 20260908-120000\n", encoding="utf-8")
            date.chmod(0o755)
            env = {**os.environ, "CLAUDE_DIR": str(target), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

            def install(selection):
                result = subprocess.run(["bash", "scripts/install.sh", selection], cwd=ROOT, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            agent = target / "agents" / "executor.md"
            agent.parent.mkdir(parents=True)
            agent.write_text("ORIGINAL_USER_COPY", encoding="utf-8")
            install("--agents-only")
            agent.write_text("SECOND_USER_COPY", encoding="utf-8")
            install("--agents-only")
            agent_backups = sorted(agent.parent.glob("executor.md.bak.20260908-120000*"))
            self.assertEqual(len(agent_backups), 2)
            self.assertEqual({path.read_text(encoding="utf-8") for path in agent_backups}, {"ORIGINAL_USER_COPY", "SECOND_USER_COPY"})

            skill = target / "skills" / "change-plan"
            skill.mkdir(parents=True)
            (skill / "user-copy.txt").write_text("ORIGINAL_SKILL_COPY", encoding="utf-8")
            install("--skills-only")
            (skill / "user-copy.txt").write_text("SECOND_SKILL_COPY", encoding="utf-8")
            install("--skills-only")
            skill_backups = sorted(skill.parent.glob("change-plan.bak.20260908-120000*"))
            self.assertEqual(len(skill_backups), 2)
            self.assertEqual(
                {(path / "user-copy.txt").read_text(encoding="utf-8") for path in skill_backups},
                {"ORIGINAL_SKILL_COPY", "SECOND_SKILL_COPY"},
            )
            self.assertFalse(any((path / "change-plan").exists() for path in skill_backups))

    def test_dangling_destination_symlinks_are_backed_up_without_writing_their_targets(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft installer symlink ") as tmp:
            root = Path(tmp)
            target = root / "Claude Config"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            date = bin_dir / "date"
            date.write_text("#!/bin/sh\necho 20260908-120000\n", encoding="utf-8")
            date.chmod(0o755)
            env = {**os.environ, "CLAUDE_DIR": str(target), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

            agent = target / "agents" / "executor.md"
            agent.parent.mkdir(parents=True)
            agent_target = root / "outside-agent.md"
            agent.symlink_to(agent_target)
            result = subprocess.run(["bash", "scripts/install.sh", "--agents-only"], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(agent_target.exists())
            self.assertFalse(agent.is_symlink())
            self.assertTrue(agent.is_file())
            self.assertTrue((agent.parent / "executor.md.bak.20260908-120000").is_symlink())

            skill = target / "skills" / "change-plan"
            skill.parent.mkdir(parents=True)
            skill_target = root / "outside-skill"
            skill.symlink_to(skill_target)
            result = subprocess.run(["bash", "scripts/install.sh", "--skills-only"], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(skill_target.exists())
            self.assertFalse(skill.is_symlink())
            self.assertTrue(skill.is_dir())
            self.assertTrue((skill.parent / "change-plan.bak.20260908-120000").is_symlink())

    def test_same_second_directory_backups_preserve_each_version_without_nesting(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft installer backup ") as tmp:
            root = Path(tmp)
            target = root / "Claude Config"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            date = bin_dir / "date"
            date.write_text("#!/bin/sh\necho 20260908-120000\n", encoding="utf-8")
            date.chmod(0o755)
            env = {**os.environ, "CLAUDE_DIR": str(target), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
            skill = target / "skills" / "change-plan"
            skill.mkdir(parents=True)
            (skill / "user-copy.txt").write_text("ORIGINAL_SKILL_COPY", encoding="utf-8")
            for copy in ("FIRST", "SECOND_SKILL_COPY"):
                result = subprocess.run(["bash", "scripts/install.sh", "--skills-only"], cwd=ROOT, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if copy == "FIRST":
                    (skill / "user-copy.txt").write_text(copy.replace("FIRST", "SECOND_SKILL_COPY"), encoding="utf-8")
            backups = sorted(skill.parent.glob("change-plan.bak.20260908-120000*"))
            self.assertEqual(len(backups), 2)
            self.assertEqual({(path / "user-copy.txt").read_text(encoding="utf-8") for path in backups}, {"ORIGINAL_SKILL_COPY", "SECOND_SKILL_COPY"})
            self.assertFalse(any((path / "change-plan").exists() for path in backups))

    def test_dangling_directory_symlink_is_backed_up_without_writing_target(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft installer symlink ") as tmp:
            root = Path(tmp)
            target = root / "Claude Config"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            date = bin_dir / "date"
            date.write_text("#!/bin/sh\necho 20260908-120000\n", encoding="utf-8")
            date.chmod(0o755)
            env = {**os.environ, "CLAUDE_DIR": str(target), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
            skill = target / "skills" / "change-plan"
            skill.parent.mkdir(parents=True)
            outside = root / "outside-skill"
            skill.symlink_to(outside)
            result = subprocess.run(["bash", "scripts/install.sh", "--skills-only"], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(outside.exists())
            self.assertFalse(skill.is_symlink())
            self.assertTrue(skill.is_dir())
            self.assertTrue((skill.parent / "change-plan.bak.20260908-120000").is_symlink())

    def test_equal_content_destination_symlinks_are_replaced_and_targets_preserved(self):
        with tempfile.TemporaryDirectory(prefix="fleetcraft installer symlink ") as tmp:
            root = Path(tmp)
            target = root / "Claude Config"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            date = bin_dir / "date"
            date.write_text("#!/bin/sh\necho 20260908-120000\n", encoding="utf-8")
            date.chmod(0o755)
            env = {**os.environ, "CLAUDE_DIR": str(target), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
            agent = target / "agents" / "executor.md"
            agent.parent.mkdir(parents=True)
            agent_outside = root / "outside-agent.md"
            agent_outside.write_text((ROOT / "agents" / "executor.md").read_text(encoding="utf-8"), encoding="utf-8")
            agent.symlink_to(agent_outside)
            result = subprocess.run(["bash", "scripts/install.sh", "--agents-only"], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(agent_outside.is_file())
            self.assertFalse(agent.is_symlink())
            self.assertTrue((agent.parent / "executor.md.bak.20260908-120000").is_symlink())
            skill = target / "skills" / "change-plan"
            skill.parent.mkdir(parents=True)
            skill_outside = root / "outside-skill"
            shutil.copytree(ROOT / "skills" / "change-plan", skill_outside)
            skill.symlink_to(skill_outside)
            result = subprocess.run(["bash", "scripts/install.sh", "--skills-only"], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(skill_outside.is_dir())
            self.assertFalse(skill.is_symlink())
            self.assertTrue((skill.parent / "change-plan.bak.20260908-120000").is_symlink())

if __name__ == "__main__": unittest.main()

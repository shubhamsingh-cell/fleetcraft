from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"
PLUGIN = ROOT / "plugins" / "fleetcraft"


class ReleaseContractTests(unittest.TestCase):
    def test_agent_skill_dependencies_are_hermetic(self) -> None:
        """Agents that rely on Fleetcraft doctrine preload its namespaced skill."""
        for name in ("executor.md", "verifier.md"):
            text = (PLUGIN / "agents" / name).read_text(encoding="utf-8")
            frontmatter, _separator, _body = text.partition("---\n\n")
            self.assertIn("skills:\n  - fleetcraft:fleet-orchestrator", frontmatter, name)
            self.assertNotIn("skills/fleet-orchestrator/", text, name)

    def test_release_toolchain_is_exactly_pinned_and_asserted(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(workflow.count("node-version: 22.22.1"), 2)
        self.assertEqual(workflow.count('test "$(node --version)" = "v22.22.1"'), 2)
        self.assertEqual(workflow.count('test "$(npm --version)" = "10.9.4"'), 2)
        self.assertEqual(workflow.count('"@anthropic-ai/claude-code": "2.1.251"'), 0)
        ci_manifest = (ROOT / ".github" / "ci" / "claude-cli" / "package.json").read_text(
            encoding="utf-8"
        )
        self.assertIn('"@anthropic-ai/claude-code": "2.1.251"', ci_manifest)

    def test_combined_distribution_license_is_declared_honestly(self) -> None:
        manifest = (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        self.assertIn('"license": "MIT AND Apache-2.0"', manifest)

    def test_workflow_local_paths_resolve_and_installed_doctor_executes(self) -> None:
        """Exercise the release-owned doctor and resolve every literal local Python path."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        relative_paths = re.findall(r"python3\s+([A-Za-z0-9_./-]+\.py)", workflow)
        self.assertTrue(relative_paths, "workflow has no literal local Python commands to verify")
        for relative in relative_paths:
            candidate = (ROOT / relative).resolve()
            self.assertTrue(candidate.is_relative_to(ROOT), relative)
            self.assertTrue(candidate.is_file(), relative)
        ci_manifest = ROOT / ".github" / "ci" / "claude-cli" / "package.json"
        self.assertTrue(ci_manifest.is_file())
        self.assertIn('python3 plugins/fleetcraft/scripts/fleetcraft-doctor.py', workflow)
        result = subprocess.run(
            [sys.executable, str(PLUGIN / "scripts" / "fleetcraft-doctor.py")],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_release_payload_license_and_notices_are_byte_identical(self) -> None:
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (PLUGIN / "LICENSE").read_bytes())
        self.assertEqual(
            (ROOT / "THIRD_PARTY_NOTICES.md").read_bytes(),
            (PLUGIN / "THIRD_PARTY_NOTICES.md").read_bytes(),
        )

    def test_public_tag_contract_is_anchored_before_and_after_install(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(workflow.count("actions/setup-node@820762786026740c76f36085b0efc47a31fe5020"), 2)
        self.assertEqual(workflow.count("package-manager-cache: false"), 2)
        self.assertNotIn("actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)
        self.assertIn("FLEETCRAFT_EVENT_SHA: ${{ github.sha }}", workflow)
        self.assertGreaterEqual(workflow.count('git fetch --force origin "refs/tags/$FLEETCRAFT_TAG:refs/tags/$FLEETCRAFT_TAG"'), 2)
        self.assertGreaterEqual(workflow.count('git rev-parse "refs/tags/$FLEETCRAFT_TAG^{commit}"'), 2)
        self.assertIn('git archive "$event_commit:plugins/fleetcraft"', workflow)
        self.assertIn('diff -ru "$FLEETCRAFT_EXPECTED_DIR" "$install_path"', workflow)
        self.assertNotIn("--exclude=", workflow)


if __name__ == "__main__":
    unittest.main()

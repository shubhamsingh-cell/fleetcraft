from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]

class PortableSourceTests(unittest.TestCase):
    def test_roles_and_routing_do_not_guarantee_private_models_or_services(self):
        text = "\n".join(path.read_text(encoding="utf-8").lower() for path in [ROOT / "skills" / "fleet-orchestrator" / "SKILL.md", *(ROOT / "agents").glob("*.md"), ROOT / "hooks" / "skill-routing-guard.py", ROOT / "hooks" / "tool-routing-guard.py"])
        for forbidden in ("claude-fable", "model: fable", "registered user-scope and connected", "api error naming the model"):
            self.assertNotIn(forbidden, text)
        self.assertIn("model: inherit", (ROOT / "agents" / "strategist.md").read_text(encoding="utf-8"))
        self.assertIn("available", (ROOT / "hooks" / "skill-routing-guard.py").read_text(encoding="utf-8").lower())

if __name__ == "__main__": unittest.main()

from pathlib import Path
import unittest


class PerformanceSkillSafetyTests(unittest.TestCase):
    def test_database_advice_does_not_present_mutations_as_read_only(self):
        text = (Path(__file__).parents[1] / "skills" / "performance-diagnosis" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertNotIn("the whole loop is read-only", text)
        self.assertNotIn("create extension hypopg", text)
        self.assertNotIn("pg_stat_statements_reset()", text)
        self.assertIn("plain `explain`", text)
        self.assertIn("known read-only", text)
        self.assertIn("do not reset shared statistics", text)


if __name__ == "__main__":
    unittest.main()

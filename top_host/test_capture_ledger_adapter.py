import unittest
from top_host.capture_ledger_adapter import validate_ledger, mark_completed


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.key = "0123456789abcdef01234567"
        self.empty = {"schema": 1, "completed": {}}

    def test_empty(self):
        self.assertEqual(validate_ledger(self.empty), self.empty)

    def test_requires_review(self):
        with self.assertRaises(ValueError):
            mark_completed(self.empty, self.key, "artifact-123", "")

    def test_requires_evidence(self):
        with self.assertRaises(ValueError):
            mark_completed(self.empty, self.key, "", "leader")

    def test_complete(self):
        updated = mark_completed(self.empty, self.key, "artifact-123", "leader")
        self.assertIn(self.key, updated["completed"])
        self.assertEqual(self.empty["completed"], {})

    def test_no_duplicate(self):
        updated = mark_completed(self.empty, self.key, "artifact-123", "leader")
        with self.assertRaises(ValueError):
            mark_completed(updated, self.key, "artifact-456", "leader")

    def test_bad_ledger(self):
        with self.assertRaises(ValueError):
            validate_ledger({"schema": 1, "completed": {"bad": {}}})


if __name__ == "__main__":
    unittest.main()

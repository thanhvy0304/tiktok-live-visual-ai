import unittest
from top_host.dedup_gate_dry_run import assess


def sample():
    return {"status": "CAPTURE_PLAN_DRY_RUN", "capture_started": False,
            "screenshots": 0, "recordings": 0, "writes_to_sheets": 0,
            "sessions": [{"schedule_id": "SCH-1", "idempotency_key": "abc",
                          "reason": "AWAITING_PLAYBACK_AND_HOST_REVIEW"}]}


class DedupGateTests(unittest.TestCase):
    def test_new_key_is_not_authorized(self):
        r = assess(sample(), {"schema": 1, "completed_keys": []})
        self.assertFalse(r["sessions"][0]["capture_authorized"])

    def test_completed_key_is_skipped(self):
        r = assess(sample(), {"schema": 1, "completed_keys": ["abc"]})
        self.assertEqual(r["sessions"][0]["decision"], "SKIP_COMPLETED")

    def test_duplicate_ledger_rejected(self):
        with self.assertRaises(ValueError):
            assess(sample(), {"schema": 1, "completed_keys": ["abc", "abc"]})

    def test_unsafe_plan_rejected(self):
        p = sample()
        p["screenshots"] = 1
        with self.assertRaises(ValueError):
            assess(p, {"schema": 1, "completed_keys": []})


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta, timezone
from top_host.capture_lock_preview import plan_claim, simulate

NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)
KEY = "a" * 24
D = {"status":"TRANSITION_CANDIDATE", "capture_key":KEY}

class LockTests(unittest.TestCase):
    def test_first(self):
        self.assertEqual(plan_claim(D, {}, NOW, "1")["status"], "CLAIM_PROPOSAL_ONLY")
    def test_active_lease(self):
        l={KEY:{"state":"CLAIMED","lease_until":(NOW+timedelta(minutes=3)).isoformat()}}
        self.assertEqual(plan_claim(D,l,NOW,"2")["reason"],"LEASE_ACTIVE")
    def test_expired_lease(self):
        l={KEY:{"state":"CLAIMED","lease_until":(NOW-timedelta(seconds=1)).isoformat()}}
        self.assertEqual(plan_claim(D,l,NOW,"3")["status"],"CLAIM_PROPOSAL_ONLY")
    def test_captured_never_retries(self):
        for state in ("CAPTURED","AWAITING_REVIEW","COMPLETED"):
            self.assertEqual(plan_claim(D,{KEY:{"state":state}},NOW,"4")["reason"],"ALREADY_CAPTURED")
    def test_failed_retries(self):
        self.assertEqual(plan_claim(D,{KEY:{"state":"FAILED"}},NOW,"5")["status"],"CLAIM_PROPOSAL_ONLY")
    def test_skip(self):
        self.assertEqual(plan_claim({"status":"SKIP"},{},NOW,"6")["reason"],"NO_TRANSITION")
    def test_simulation(self):
        self.assertEqual(simulate()["status"],"LOCK_SIMULATION_OK")

if __name__ == "__main__": unittest.main()

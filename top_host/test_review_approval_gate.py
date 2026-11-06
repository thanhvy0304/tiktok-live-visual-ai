import unittest
from top_host.review_approval_gate import approval_decision

KEY = "0123456789abcdef01234567"

def inputs():
    capture = {"status": "FRAME_FOR_LEADER_REVIEW", "screenshot_count": 1,
               "playback_observed": True, "host_identity_verified": False,
               "schedule_id": "SCH-TEST"}
    review = {"schedule_id": "SCH-TEST", "idempotency_key": KEY, "decision": "APPROVE",
              "reviewer": "leader", "evidence_ref": "artifact-123",
              "confirmed_host_matches_schedule": True}
    ledger = {"schema": 1, "completed": {}}
    return capture, review, ledger

class ApprovalTests(unittest.TestCase):
    def test_approved_review(self):
        self.assertTrue(approval_decision(*inputs())["approved"])
    def test_missing_frame(self):
        c,r,l = inputs(); c["screenshot_count"] = 0
        self.assertFalse(approval_decision(c,r,l)["approved"])
    def test_wrong_host(self):
        c,r,l = inputs(); r["confirmed_host_matches_schedule"] = False
        self.assertFalse(approval_decision(c,r,l)["approved"])
    def test_rejected(self):
        c,r,l = inputs(); r["decision"] = "REJECT"
        self.assertFalse(approval_decision(c,r,l)["approved"])
    def test_schedule_mismatch(self):
        c,r,l = inputs(); r["schedule_id"] = "OTHER"
        self.assertFalse(approval_decision(c,r,l)["approved"])
    def test_completed(self):
        c,r,l = inputs(); l["completed"][KEY] = {"evidence_ref": "old", "reviewed_by": "leader"}
        self.assertEqual(approval_decision(c,r,l)["reason"], "ALREADY_COMPLETED")
    def test_no_reviewer(self):
        c,r,l = inputs(); r["reviewer"] = ""
        self.assertFalse(approval_decision(c,r,l)["approved"])
    def test_invalid_key(self):
        c,r,l = inputs(); r["idempotency_key"] = "bad"
        self.assertFalse(approval_decision(c,r,l)["approved"])

if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from top_host.e2e_dry_run import integrate

NOW = datetime(2026, 11, 6, 15, 5, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
def handoff():
    return {"status": "CAPTURE_HANDOFF_PREVIEW_OK", "date_vn": "06/11/2026",
            "writes_to_sheets": 0, "recordings": 0, "capture_started": False,
            "sessions": [{"schedule_id": "SCH-TEST", "host": "Thanh Huyền",
                          "channel": "Tiktok Tích Xanh",
                          "live_url": "https://www.tiktok.com/@hannaholala/live",
                          "start_vn": "2026-11-06T15:00:00+07:00",
                          "end_vn": "2026-11-06T17:00:00+07:00"}]}

class IntegrationTests(unittest.TestCase):
    def test_active_still_denied(self):
        r = integrate(handoff(), {"schema": 1, "completed": {}}, NOW)
        self.assertEqual(r["status"], "E2E_DRY_RUN_PASS")
        self.assertFalse(r["sessions"][0]["capture_authorized"])
        self.assertEqual(r["sessions"][0]["approval_decision"], "NO_VALID_FRAME")
    def test_completed_skipped(self):
        h = handoff()
        first = integrate(h, {"schema": 1, "completed": {}}, NOW)
        from top_host.capture_plan_dry_run import plan
        key = plan(h, NOW)["sessions"][0]["idempotency_key"]
        ledger = {"schema": 1, "completed": {key: {"evidence_ref": "artifact-123", "reviewed_by": "leader"}}}
        r = integrate(h, ledger, NOW)
        self.assertEqual(r["sessions"][0]["dedup_decision"], "SKIP_COMPLETED")
    def test_missing_host_fails(self):
        h = handoff(); h["sessions"][0]["host"] = ""
        with self.assertRaises(ValueError):
            integrate(h, {"schema": 1, "completed": {}}, NOW)
    def test_stale_fails(self):
        h = handoff(); h["date_vn"] = "05/11/2026"
        with self.assertRaises(ValueError):
            integrate(h, {"schema": 1, "completed": {}}, NOW)
    def test_no_screenshot_or_writes(self):
        r = integrate(handoff(), {"schema": 1, "completed": {}}, NOW)
        self.assertEqual((r["screenshots"], r["ledger_writes"], r["writes_to_sheets"]), (0, 0, 0))

if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from top_host.capture_plan_dry_run import plan

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
NOW = datetime(2026, 11, 6, 15, 5, tzinfo=TZ)


def handoff():
    return {"status": "CAPTURE_HANDOFF_PREVIEW_OK", "date_vn": "06/11/2026",
            "writes_to_sheets": 0, "recordings": 0, "capture_started": False,
            "sessions": [{"schedule_id": "SCH-TEST", "host": "Thanh Huyền",
                          "channel": "Tiktok Tích Xanh",
                          "live_url": "https://www.tiktok.com/@hannaholala/live",
                          "start_vn": "2026-11-06T15:00:00+07:00",
                          "end_vn": "2026-11-06T17:00:00+07:00"}]}


class TestPlan(unittest.TestCase):
    def test_active_is_not_authorized(self):
        s = plan(handoff(), NOW)["sessions"][0]
        self.assertTrue(s["scheduled_active"])
        self.assertFalse(s["capture_authorized"])
        self.assertEqual(s["reason"], "AWAITING_PLAYBACK_AND_HOST_REVIEW")

    def test_outside_window(self):
        self.assertEqual(plan(handoff(), NOW - timedelta(hours=3))["sessions"][0]["reason"], "OUTSIDE_WINDOW")

    def test_deterministic_key(self):
        first = plan(handoff(), NOW)["sessions"][0]["idempotency_key"]
        self.assertEqual(first, plan(handoff(), NOW)["sessions"][0]["idempotency_key"])
        self.assertEqual(plan(handoff(), NOW, [first])["sessions"][0]["reason"], "ALREADY_CAPTURED")

    def test_missing_host_rejected(self):
        h = handoff()
        h["sessions"][0]["host"] = ""
        with self.assertRaises(ValueError):
            plan(h, NOW)

    def test_duplicate_rejected(self):
        h = handoff()
        h["sessions"].append(dict(h["sessions"][0]))
        with self.assertRaises(ValueError):
            plan(h, NOW)

    def test_stale_rejected(self):
        h = handoff()
        h["date_vn"] = "05/11/2026"
        with self.assertRaises(ValueError):
            plan(h, NOW)


if __name__ == "__main__":
    unittest.main()

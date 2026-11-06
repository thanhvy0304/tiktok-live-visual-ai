"""Offline safety tests for STEP 07 handoff preview."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

from top_host import capture_handoff_preview as handoff


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.input = Path(self.temp.name) / "schedule.json"
        self.output = Path(self.temp.name) / "handoff.json"
        self.date = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y")
        self.sample = {
            "status": "TOP_HOST_SCHEDULE_SYNC_OK", "date_vn": self.date,
            "channel": "Tiktok Tích Xanh", "writes_to_sheets": 0,
            "recordings": 0, "capture": False, "matched_sessions": 1,
            "sessions": [{"schedule_id": "SCH-TEST-1", "host": "Thanh Huyền",
                          "channel": "Tiktok Tích Xanh", "date_vn": self.date,
                          "start": "15h", "end": "18h"}],
        }

    def run_handoff(self):
        self.input.write_text(json.dumps(self.sample), encoding="utf-8")
        with patch.object(handoff, "INPUT", self.input), patch.object(handoff, "OUTPUT", self.output):
            handoff.main()
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_read_only(self):
        output = self.run_handoff()
        self.assertEqual(output["status"], "CAPTURE_HANDOFF_PREVIEW_OK")
        self.assertEqual(output["recordings"], 0)
        self.assertEqual(output["writes_to_sheets"], 0)
        self.assertFalse(output["capture_started"])
        self.assertFalse(output["sessions"][0]["capture_requested"])

    def test_reject_duplicate_id(self):
        self.sample["sessions"].append(dict(self.sample["sessions"][0]))
        self.sample["matched_sessions"] = 2
        with self.assertRaises(ValueError):
            self.run_handoff()

    def test_reject_unexpected_host(self):
        self.sample["sessions"][0]["host"] = "Other Host"
        with self.assertRaises(ValueError):
            self.run_handoff()

    def test_reject_capture_enabled(self):
        self.sample["capture"] = True
        with self.assertRaises(ValueError):
            self.run_handoff()

    def test_reject_stale_date(self):
        self.sample["date_vn"] = "01/01/2020"
        with self.assertRaises(ValueError):
            self.run_handoff()

    def test_reject_invalid_time(self):
        self.sample["sessions"][0]["start"] = "99h"
        with self.assertRaises(ValueError):
            self.run_handoff()


if __name__ == "__main__":
    unittest.main()

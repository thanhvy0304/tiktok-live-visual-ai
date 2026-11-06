import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from top_host.transition_decision import decide

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
now = datetime(2026, 11, 6, 14, 5, tzinfo=TZ)
def handoff(sessions=None):
    return {"status":"CAPTURE_HANDOFF_PREVIEW_OK", "date_vn":"06/11/2026",
            "writes_to_sheets":0, "capture_started":False,
            "sessions":sessions if sessions is not None else [{
                "schedule_id":"SCH-1", "host":"Thanh Huyền",
                "channel":"Tiktok Tích Xanh",
                "start_vn":"2026-11-06T14:00:00+07:00",
                "end_vn":"2026-11-06T16:00:00+07:00"}]}
class Tests(unittest.TestCase):
    def test_transition(self):
        a=decide(handoff(),now)
        self.assertEqual(a["status"],"TRANSITION_CANDIDATE")
        self.assertTrue(a["requires_atomic_claim"])
        self.assertEqual(a["capture_key"],decide(handoff(),now)["capture_key"])
    def test_later_not_trigger(self):
        self.assertEqual(decide(handoff(),now+timedelta(minutes=15))["status"],"SKIP")
    def test_early_not_trigger(self):
        self.assertEqual(decide(handoff(),now-timedelta(minutes=10))["status"],"SKIP")
    def test_ambiguous(self):
        s=handoff()["sessions"][0]
        self.assertEqual(decide(handoff([s,s]),now)["status"],"SKIP")
    def test_stale(self):
        self.assertEqual(decide(handoff(),now+timedelta(days=1))["reason"],"STALE_DATE")
    def test_unsafe(self):
        h=handoff();h["capture_started"]=True
        with self.assertRaises(ValueError): decide(h,now)
if __name__=="__main__": unittest.main()

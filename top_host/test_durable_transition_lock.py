import unittest
from datetime import datetime, timedelta, timezone
from top_host.durable_transition_lock import claim

NOW=datetime(2026,11,6,tzinfo=timezone.utc)
KEY="b"*24
D={"status":"TRANSITION_CANDIDATE","capture_key":KEY,
   "schedule_id":"SCH-1","scheduled_host":"Thanh Huyền"}
class Tests(unittest.TestCase):
    def test_claim(self):
        result, ledger=claim(D,{"schema":1,"entries":{}},NOW,"run1")
        self.assertEqual(result["status"],"LEASE_CLAIM_READY")
        self.assertEqual(ledger["entries"][KEY]["state"],"CLAIMED")
        duplicate,_=claim(D,ledger,NOW,"run2")
        self.assertEqual(duplicate["reason"],"LEASE_ACTIVE")
    def test_expired_retry(self):
        _,ledger=claim(D,{"schema":1,"entries":{}},NOW,"run1")
        retry,_=claim(D,ledger,NOW+timedelta(seconds=181),"run2")
        self.assertEqual(retry["status"],"LEASE_CLAIM_READY")
    def test_captured_blocked(self):
        ledger={"schema":1,"entries":{KEY:{"state":"AWAITING_REVIEW"}}}
        result,_=claim(D,ledger,NOW,"run3")
        self.assertEqual(result["reason"],"ALREADY_CAPTURED")
if __name__=="__main__":unittest.main()

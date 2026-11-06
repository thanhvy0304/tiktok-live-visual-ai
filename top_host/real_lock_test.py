"""STEP 17.3.1: real GitHub Contents write/read/delete test, isolated from production.

Uses a unique test file, no LIVE capture and no production ledger writes.
"""
import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError

from top_host.durable_transition_lock import claim, request

OUT = Path("top_host/output/real_lock_test.json")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    run_id = os.environ["GITHUB_RUN_ID"]
    if not run_id.isdigit():
        raise ValueError("Invalid run id")
    path = f"top_host/state/tests/lease_test_{run_id}.json"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    key = hashlib.sha256(f"ISOLATED_TEST|{run_id}".encode()).hexdigest()[:24]
    decision = {"status": "TRANSITION_CANDIDATE", "capture_key": key,
                "schedule_id": "TEST-ONLY", "scheduled_host": "TEST-ONLY"}
    now = datetime.now(timezone.utc)
    result = {"status": "TEST_FAILED", "test_only": True, "capture_started": False,
              "production_ledger_untouched": True}
    sha = None
    try:
        initial = {"schema": 1, "entries": {}}
        first, claimed = claim(decision, initial, now, run_id)
        assert first["status"] == "LEASE_CLAIM_READY"
        payload = {"message": "Test isolated Top Host lease claim",
                   "branch": "main", "content": base64.b64encode(
                       (json.dumps(claimed, ensure_ascii=False) + "\n").encode()).decode()}
        response = request(url, token, "PUT", payload)
        sha = response["content"]["sha"]
        stored = request(url + "?ref=main", token)
        sha = stored["sha"]
        persisted = json.loads(base64.b64decode(stored["content"]).decode())
        assert persisted["entries"][key]["run_id"] == run_id
        second, _ = claim(decision, persisted, now, run_id + "-duplicate")
        assert second.get("reason") == "LEASE_ACTIVE"
        retry, _ = claim(decision, persisted, now + timedelta(seconds=181), run_id + "-retry")
        assert retry["status"] == "LEASE_CLAIM_READY"
        result.update(status="REAL_LOCK_TEST_PASS",
                      write_read="PASS", duplicate="LEASE_ACTIVE",
                      expired_lease="RETRY_ALLOWED")
    finally:
        if sha:
            try:
                request(url, token, "DELETE", {"message": "Remove isolated Top Host lease test",
                                              "sha": sha, "branch": "main"})
                result["cleanup"] = "DELETED"
            except HTTPError as exc:
                result["cleanup"] = f"FAILED_HTTP_{exc.code}"
                result["status"] = "TEST_FAILED"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "REAL_LOCK_TEST_PASS":
        raise RuntimeError("Real lock test failed")


if __name__ == "__main__":
    main()

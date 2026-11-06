"""STEP 17.2: offline state-machine simulation for one capture per session.

This module never claims a real lock. Production requires durable conditional
storage and workflow concurrency before enabling automated capture.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTPUT = Path("top_host/output/lock_preview.json")
LEASE_SECONDS = 180


def plan_claim(decision, ledger, now, run_id):
    if now.tzinfo is None or not run_id:
        raise ValueError("Timezone and run_id required")
    if decision.get("status") != "TRANSITION_CANDIDATE":
        return {"status": "SKIP", "reason": "NO_TRANSITION"}
    key = decision.get("capture_key")
    if not isinstance(key, str) or len(key) != 24 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("Invalid capture key")
    item = ledger.get(key)
    if item:
        state = item.get("state")
        if state in ("CAPTURED", "AWAITING_REVIEW", "COMPLETED"):
            return {"status": "SKIP", "reason": "ALREADY_CAPTURED"}
        if state == "CLAIMED":
            until = datetime.fromisoformat(item["lease_until"])
            if until.tzinfo is None:
                raise ValueError("Invalid lease timezone")
            if now < until:
                return {"status": "SKIP", "reason": "LEASE_ACTIVE"}
        elif state != "FAILED":
            raise ValueError("Unknown ledger state")
    lease = now + timedelta(seconds=LEASE_SECONDS)
    return {"status": "CLAIM_PROPOSAL_ONLY", "capture_key": key,
            "run_id": str(run_id), "lease_until": lease.isoformat(),
            "requires_atomic_write": True, "capture_started": False}


def simulate():
    now = datetime.now(timezone.utc)
    key = "a" * 24
    decision = {"status": "TRANSITION_CANDIDATE", "capture_key": key}
    first = plan_claim(decision, {}, now, "run-1")
    claimed = {key: {"state": "CLAIMED", "lease_until": first["lease_until"]}}
    duplicate = plan_claim(decision, claimed, now, "run-2")
    retry = plan_claim(decision, claimed, now + timedelta(seconds=LEASE_SECONDS + 1), "run-3")
    captured = plan_claim(decision, {key: {"state": "AWAITING_REVIEW"}}, now + timedelta(hours=1), "run-4")
    return {"status": "LOCK_SIMULATION_OK", "first": first["status"],
            "concurrent": duplicate["reason"], "after_expiry": retry["status"],
            "after_capture": captured["reason"],
            "durable_lock_enabled": False, "capture_started": False}


def main():
    result = simulate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

"""STEP 11: persistent idempotency gate using GitHub Actions cache (dry-run only).

Cache is advisory, not a transactional lock. This module deliberately never
claims capture completed or writes a capture marker.
"""
import json
import os
from pathlib import Path

INPUT = Path("top_host/output/capture_plan_dry_run.json")
OUTPUT = Path("top_host/output/dedup_gate_dry_run.json")
LEDGER = Path("top_host/state/captured_keys.json")


def assess(plan, ledger):
    if plan.get("status") != "CAPTURE_PLAN_DRY_RUN" or plan.get("capture_started") is not False:
        raise ValueError("Unsafe plan")
    if plan.get("screenshots") != 0 or plan.get("recordings") != 0 or plan.get("writes_to_sheets") != 0:
        raise ValueError("Unsafe plan counters")
    if not isinstance(ledger, dict) or ledger.get("schema") != 1 or not isinstance(ledger.get("completed_keys"), list):
        raise ValueError("Invalid ledger")
    keys = ledger["completed_keys"]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate ledger keys")
    rows = []
    for s in plan.get("sessions", []):
        key = s["idempotency_key"]
        rows.append({"schedule_id": s["schedule_id"], "idempotency_key": key,
                     "already_completed": key in keys,
                     "decision": "SKIP_COMPLETED" if key in keys else s["reason"],
                     "capture_authorized": False})
    return {"status": "DEDUP_GATE_DRY_RUN", "sessions": rows,
            "persistent_ledger_available": LEDGER.exists(),
            "capture_started": False, "screenshots": 0, "recordings": 0,
            "writes_to_sheets": 0,
            "note": "Dry-run only. No capture marker written. Cache-based state is not atomic and may be evicted."}


def main():
    plan = json.loads(INPUT.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {"schema": 1, "completed_keys": []}
    result = assess(plan, ledger)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

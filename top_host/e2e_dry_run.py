"""STEP 14: safe end-to-end orchestration report. No capture or ledger writes."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from top_host.capture_plan_dry_run import plan
from top_host.dedup_gate_dry_run import assess
from top_host.review_approval_gate import approval_decision
from top_host.capture_ledger_adapter import validate_ledger

ROOT = Path("top_host/output")
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def integrate(handoff, ledger, now):
    validate_ledger(ledger)
    capture_plan = plan(handoff, now, set(ledger["completed"]))
    dedup = assess(capture_plan, {"schema": 1, "completed_keys": list(ledger["completed"])})
    decisions = []
    for row in dedup["sessions"]:
        # A deliberately unverified sample: approval must fail closed.
        capture = {"status": "NOT_CAPTURED", "screenshot_count": 0,
                   "playback_observed": False, "host_identity_verified": False,
                   "schedule_id": row["schedule_id"]}
        review = {"schedule_id": row["schedule_id"],
                  "idempotency_key": row["idempotency_key"],
                  "decision": "PENDING", "reviewer": "", "evidence_ref": "",
                  "confirmed_host_matches_schedule": False}
        approval = approval_decision(capture, review, ledger)
        if approval["approved"]:
            raise RuntimeError("Unsafe approval of unverified evidence")
        decisions.append({"schedule_id": row["schedule_id"],
                          "dedup_decision": row["decision"],
                          "approval_decision": approval["reason"],
                          "capture_authorized": False})
    return {"status": "E2E_DRY_RUN_PASS", "generated_at_vn": now.isoformat(),
            "sessions": decisions, "writes_to_sheets": 0,
            "screenshots": 0, "recordings": 0, "ledger_writes": 0,
            "capture_started": False,
            "limitations": ["No real playback evidence consumed",
                            "No durable capture lock or production ledger writes",
                            "Leader review remains manual"]}


def main():
    handoff = json.loads((ROOT / "capture_handoff.json").read_text(encoding="utf-8"))
    ledger = {"schema": 1, "completed": {}}
    result = integrate(handoff, ledger, datetime.now(TZ))
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "e2e_dry_run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

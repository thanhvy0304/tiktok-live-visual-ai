"""STEP 13: offline review approval gate; does not record, upload, or mark complete."""
from datetime import datetime
from zoneinfo import ZoneInfo

def approval_decision(capture, review, ledger):
    if capture.get("status") != "FRAME_FOR_LEADER_REVIEW" or capture.get("screenshot_count") != 1 or capture.get("playback_observed") is not True:
        return {"approved": False, "reason": "NO_VALID_FRAME"}
    if capture.get("host_identity_verified") is not False:
        return {"approved": False, "reason": "UNEXPECTED_CAPTURE_IDENTITY_FLAG"}
    key = review.get("idempotency_key")
    if not isinstance(key, str) or len(key) != 24 or any(c not in "0123456789abcdef" for c in key):
        return {"approved": False, "reason": "INVALID_KEY"}
    if review.get("schedule_id") != capture.get("schedule_id"):
        return {"approved": False, "reason": "SCHEDULE_MISMATCH"}
    if review.get("decision") != "APPROVE" or not review.get("reviewer") or not review.get("evidence_ref"):
        return {"approved": False, "reason": "REVIEW_NOT_APPROVED"}
    if not review.get("confirmed_host_matches_schedule"):
        return {"approved": False, "reason": "HOST_NOT_CONFIRMED"}
    if key in ledger.get("completed", {}):
        return {"approved": False, "reason": "ALREADY_COMPLETED"}
    return {"approved": True, "reason": "READY_FOR_SEPARATE_LEDGER_COMMIT",
            "idempotency_key": key, "schedule_id": capture["schedule_id"],
            "note": "Approval alone does not write a ledger or ensure distributed capture exclusivity."}

"""STEP 10: deterministic capture plan only; no browser, screenshot, or writes to Sheets."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("top_host/output")
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
URL = "https://www.tiktok.com/@hannaholala/live"


def plan(handoff, now, already_captured=None):
    already_captured = set(already_captured or [])
    if handoff.get("status") != "CAPTURE_HANDOFF_PREVIEW_OK":
        raise ValueError("Invalid handoff")
    if handoff.get("date_vn") != now.strftime("%d/%m/%Y"):
        raise ValueError("Stale schedule")
    if handoff.get("writes_to_sheets") != 0 or handoff.get("recordings") != 0 or handoff.get("capture_started") is not False:
        raise ValueError("Unsafe handoff")
    sessions = handoff.get("sessions", [])
    if not isinstance(sessions, list):
        raise ValueError("Invalid sessions")
    seen = set()
    decisions = []
    for s in sessions:
        sid = s.get("schedule_id", "")
        if not sid or sid in seen:
            raise ValueError("Duplicate or missing schedule ID")
        seen.add(sid)
        if not s.get("host", "").strip() or s.get("channel") != "Tiktok Tích Xanh" or s.get("live_url") != URL:
            raise ValueError("Unexpected capture target")
        start, end = datetime.fromisoformat(s["start_vn"]), datetime.fromisoformat(s["end_vn"])
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("Invalid time window")
        key = hashlib.sha256(f"{sid}|{start.isoformat()}|FIRST_FRAME".encode()).hexdigest()[:24]
        active = start <= now < end
        reason = "OUTSIDE_WINDOW" if not active else ("ALREADY_CAPTURED" if key in already_captured else "AWAITING_PLAYBACK_AND_HOST_REVIEW")
        decisions.append({"schedule_id": sid, "host": s["host"], "idempotency_key": key,
                          "scheduled_active": active, "reason": reason,
                          "capture_authorized": False})
    return {"status": "CAPTURE_PLAN_DRY_RUN", "generated_at_vn": now.isoformat(),
            "sessions": decisions, "capture_started": False, "screenshots": 0,
            "recordings": 0, "writes_to_sheets": 0,
            "note": "Keys are deterministic only; persistent deduplication storage and identity verification are NOT implemented."}


def main():
    handoff = json.loads((ROOT / "capture_handoff.json").read_text(encoding="utf-8"))
    result = plan(handoff, datetime.now(TZ))
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "capture_plan_dry_run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

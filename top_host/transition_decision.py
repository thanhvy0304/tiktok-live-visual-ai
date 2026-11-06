"""STEP 17.1: deterministic, read-only trigger decision for host transitions.

No screenshots, GitHub writes or scheduled jobs. Designed for a future
scheduler; a durable atomic claim must be added before enabling capture.
"""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
INPUT = Path("top_host/output/capture_handoff.json")
OUTPUT = Path("top_host/output/transition_decision.json")


def decide(handoff, now=None, window_minutes=10):
    now = now or datetime.now(TZ)
    if now.tzinfo is None:
        raise ValueError("Timezone-aware now required")
    if handoff.get("status") != "CAPTURE_HANDOFF_PREVIEW_OK":
        raise ValueError("Invalid handoff")
    if handoff.get("writes_to_sheets") != 0 or handoff.get("capture_started") is not False:
        raise ValueError("Unsafe handoff")
    if handoff.get("date_vn") != now.astimezone(TZ).strftime("%d/%m/%Y"):
        return {"status": "SKIP", "reason": "STALE_DATE"}
    eligible = []
    for s in handoff.get("sessions", []):
        start, end = datetime.fromisoformat(s["start_vn"]), datetime.fromisoformat(s["end_vn"])
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("Timezone missing")
        if s.get("channel") != "Tiktok Tích Xanh" or not s.get("host") or not s.get("schedule_id"):
            raise ValueError("Invalid session")
        if start <= now < min(end, start + timedelta(minutes=window_minutes)):
            eligible.append(s)
    if len(eligible) != 1:
        return {"status": "SKIP", "reason": "NO_UNIQUE_TRANSITION", "matching_sessions": len(eligible)}
    s = eligible[0]
    key = hashlib.sha256(f'{s["schedule_id"]}|{s["start_vn"]}|FIRST_FRAME'.encode()).hexdigest()[:24]
    return {"status": "TRANSITION_CANDIDATE", "capture_started": False,
            "requires_atomic_claim": True, "schedule_id": s["schedule_id"],
            "scheduled_host": s["host"], "start_vn": s["start_vn"],
            "capture_key": key, "note": "Not permission to capture; durable claim missing."}


def main():
    handoff = json.loads(INPUT.read_text(encoding="utf-8"))
    decision = decide(handoff)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, ensure_ascii=False))


if __name__ == "__main__":
    main()

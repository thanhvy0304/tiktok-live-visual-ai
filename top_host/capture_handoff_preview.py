"""STEP 07: validate Top Host schedule and prepare a safe capture handoff (no recording)."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

INPUT = Path("top_host/output/schedule_sync.json")
OUTPUT = Path("top_host/output/capture_handoff.json")
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
CHANNEL = "Tiktok Tích Xanh"
LIVE_URL = "https://www.tiktok.com/@hannaholala/live"

def minutes(raw):
    import re
    m = re.fullmatch(r"(\d{1,2})h(\d{1,2})?", str(raw).strip(), re.I)
    if not m:
        raise ValueError(f"Invalid time: {raw!r}")
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    if hour > 24 or minute > 59 or (hour == 24 and minute):
        raise ValueError(f"Invalid time: {raw!r}")
    return hour * 60 + minute

def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    if data.get("status") != "TOP_HOST_SCHEDULE_SYNC_OK" or data.get("channel") != CHANNEL:
        raise ValueError("Unexpected schedule export")
    if data.get("writes_to_sheets") != 0 or data.get("recordings") != 0 or data.get("capture") is not False:
        raise ValueError("Unsafe schedule export flags")
    now = datetime.now(TZ)
    expected_date = now.strftime("%d/%m/%Y")
    if data.get("date_vn") != expected_date:
        raise ValueError("Schedule date is stale")
    sessions = data.get("sessions", [])
    if not isinstance(sessions, list) or data.get("matched_sessions") != len(sessions):
        raise ValueError("Session count mismatch")
    seen, handoffs = set(), []
    for item in sessions:
        sid = str(item.get("schedule_id", "")).strip()
        if not sid or sid in seen or item.get("channel") != CHANNEL or item.get("date_vn") != expected_date:
            raise ValueError("Invalid or duplicate session")
        seen.add(sid)
        if not str(item.get("host", "")).strip():
            raise ValueError("Unexpected host")
        start, end = minutes(item.get("start")), minutes(item.get("end"))
        if end <= start:
            end += 1440
        if end - start > 12 * 60:
            raise ValueError("Session duration exceeds safety limit")
        base = datetime.strptime(expected_date, "%d/%m/%Y").replace(tzinfo=TZ)
        start_dt, end_dt = base + timedelta(minutes=start), base + timedelta(minutes=end)
        state = "UPCOMING" if now < start_dt else ("ACTIVE" if now < end_dt else "ENDED")
        handoffs.append({
            "schedule_id": sid, "host": item["host"], "channel": CHANNEL,
            "live_url": LIVE_URL, "start_vn": start_dt.isoformat(),
            "end_vn": end_dt.isoformat(), "state_at_generation": state,
            "eligible_for_capture": state == "ACTIVE",
            "capture_requested": False,
        })
    output = {
        "status": "CAPTURE_HANDOFF_PREVIEW_OK",
        "generated_at_vn": now.isoformat(),
        "date_vn": expected_date,
        "session_count": len(handoffs),
        "active_sessions": sum(s["state_at_generation"] == "ACTIVE" for s in handoffs),
        "sessions": handoffs,
        "writes_to_sheets": 0, "recordings": 0, "capture_started": False,
        "note": "Read-only preview; ACTIVE is not evidence that TikTok LIVE is online."
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()

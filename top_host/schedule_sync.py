"""Read-only LIVE_SCHEDULE export for TikTok Tích Xanh.
Requires GitHub secret TOP_HOST_GOOGLE_CREDENTIALS_JSON (service account with Viewer
access to the spreadsheet). No writes, capture, or production API calls.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

SHEET_ID = "1XWj-zSMcb2W5fPqKT8LptOwSwCFpEQ_4MYl5keIihXE"
SHEET = "LIVE_SCHEDULE"
CHANNEL = "tiktok tích xanh"
LIVE_URL = "https://www.tiktok.com/@hannaholala/live"
OUT = Path("top_host_output")


def parse_time(value):
    match = re.fullmatch(r"(\d{1,2})h(\d{1,2})?", str(value).strip(), re.I)
    if not match:
        raise ValueError("Invalid time")
    hour, minute = int(match[1]), int(match[2] or 0)
    if hour > 24 or minute > 59 or (hour == 24 and minute):
        raise ValueError("Invalid time")
    return hour * 60 + minute


def get_values():
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    secret = os.environ.get("TOP_HOST_GOOGLE_CREDENTIALS_JSON", "")
    if not secret:
        raise RuntimeError("Missing TOP_HOST_GOOGLE_CREDENTIALS_JSON secret")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(secret), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    url = ("https://sheets.googleapis.com/v4/spreadsheets/" + SHEET_ID
           + "/values/" + quote(SHEET + "!A:I", safe="")
           + "?valueRenderOption=FORMATTED_VALUE")
    response = AuthorizedSession(credentials).get(url, timeout=45)
    response.raise_for_status()
    return response.json().get("values", [])


def build(rows, date_filter):
    if not rows:
        raise ValueError("Sheet has no rows")
    headers = [str(v).strip() for v in rows[0]]
    required = ("Schedule_ID", "CHANNEL", "DATE", "START", "END", "Host_Name")
    if any(k not in headers for k in required):
        raise ValueError("Missing required header(s)")
    ix = {key: headers.index(key) for key in required}
    results, seen = [], set()
    for row_number, row in enumerate(rows[1:], 2):
        def cell(key):
            index = ix[key]
            return str(row[index]).strip() if index < len(row) else ""
        if cell("CHANNEL").casefold() != CHANNEL:
            continue
        try:
            date = datetime.strptime(cell("DATE"), "%d/%m/%Y").strftime("%Y-%m-%d")
            start, end = parse_time(cell("START")), parse_time(cell("END"))
        except ValueError as exc:
            raise ValueError(f"Invalid date/time on row {row_number}") from exc
        if date != date_filter:
            continue
        sid, host = cell("Schedule_ID"), cell("Host_Name")
        if not sid or not host or end <= start:
            raise ValueError(f"Missing ID/Host or invalid interval on row {row_number}")
        if sid in seen:
            raise ValueError(f"Duplicate Schedule_ID: {sid}")
        seen.add(sid)
        results.append({
            "schedule_id": sid, "channel": cell("CHANNEL"), "date_vn": date,
            "start_minute": start, "end_minute": end, "host_name": host,
            "live_url": LIVE_URL, "sheet_row": row_number
        })
    return sorted(results, key=lambda s: (s["start_minute"], s["schedule_id"]))


def main():
    date = os.environ.get("TOP_HOST_DATE", "").strip()
    date = date or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d")
    datetime.strptime(date, "%Y-%m-%d")
    sessions = build(get_values(), date)
    OUT.mkdir(exist_ok=True)
    report = {"mode": "DRY_RUN", "timezone": "Asia/Ho_Chi_Minh",
              "date": date, "count": len(sessions), "sessions": sessions}
    (OUT / "schedule_dry_run.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DRY RUN | {date} | {len(sessions)} sessions")
    for session in sessions:
        print(session["schedule_id"], session["host_name"],
              session["start_minute"], session["end_minute"])
    print("Read only: no sheet updates, recorder calls, or production API actions.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

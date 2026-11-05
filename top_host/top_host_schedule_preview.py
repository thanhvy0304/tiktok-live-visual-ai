"""Top Host schedule preview. Read-only; no capture, writes, or uploads."""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

from google.auth import default
from google.auth.transport.requests import AuthorizedSession

SHEET_ID = "1XWj-zSMcb2W5fPqKT8LptOwSwCFpEQ_4MYl5keIihXE"
RANGE = "'LIVE_SCHEDULE'!A1:AZ10000"
CHANNEL = "Tiktok Tích Xanh"
TOP_HOSTS = {"thanh huyền"}
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def main():
    today = datetime.now(TZ).strftime("%d/%m/%Y")
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{quote(RANGE, safe='')}"
    response = AuthorizedSession(credentials).get(url, timeout=40)
    if not response.ok:
        raise RuntimeError(f"Sheets read failed: HTTP {response.status_code}; check API and viewer access")
    rows = response.json().get("values", [])
    if not rows:
        raise RuntimeError("LIVE_SCHEDULE empty")
    headers = [str(x).strip().casefold() for x in rows[0]]

    def index(name, required=True):
        try:
            return headers.index(name.casefold())
        except ValueError:
            if required:
                raise RuntimeError(f"Missing column: {name}")
            return None

    columns = {name: index(name) for name in ("CHANNEL", "DATE", "START", "END", "Host_Name")}
    schedule_col = index("Schedule_ID", required=False)

    def cell(row, col):
        return str(row[col]).strip() if col is not None and col < len(row) else ""

    sessions = []
    for row in rows[1:]:
        if cell(row, columns["CHANNEL"]).casefold() != CHANNEL.casefold():
            continue
        if cell(row, columns["DATE"]) != today:
            continue
        host = cell(row, columns["Host_Name"])
        if host.casefold() not in TOP_HOSTS:
            continue
        sessions.append({
            "schedule_id": cell(row, schedule_col),
            "host": host,
            "channel": CHANNEL,
            "date_vn": today,
            "start": cell(row, columns["START"]),
            "end": cell(row, columns["END"]),
            "selection": "TOP_HOST_MATCH",
        })
    print(json.dumps({
        "status": "TOP_HOST_PREVIEW_OK",
        "date_vn": today,
        "channel": CHANNEL,
        "top_hosts": sorted(TOP_HOSTS),
        "matched_sessions": len(sessions),
        "sessions": sessions,
        "writes": 0,
        "recordings": 0,
        "capture": False
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

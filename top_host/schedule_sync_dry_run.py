"""Read-only Schedule Sync dry run. No writes, recordings or external uploads."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from google.auth import default
from google.auth.transport.requests import AuthorizedSession

SHEET_ID = "1XWj-zSMcb2W5fPqKT8LptOwSwCFpEQ_4MYl5keIihXE"
RANGE = "'LIVE_SCHEDULE'!A1:AZ10000"
CHANNEL = "Tiktok Tích Xanh"

def main():
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    session = AuthorizedSession(credentials)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{RANGE}"
    response = session.get(url, timeout=40)
    if not response.ok:
        try:
            err = response.json().get("error", {})
            details = {"code": err.get("code"), "status": err.get("status"),
                       "message": err.get("message"), "details": err.get("details", [])}
        except ValueError:
            details = {"http_status": response.status_code, "body": response.text[:1500]}
        raise RuntimeError("GOOGLE_SHEETS_API_ERROR " + json.dumps(details, ensure_ascii=False))
    rows = response.json().get("values", [])
    if not rows:
        raise RuntimeError("LIVE_SCHEDULE empty")
    header = [str(x).strip().casefold() for x in rows[0]]
    def idx(name):
        key = name.casefold()
        if key not in header:
            raise RuntimeError(f"Missing required column: {name}")
        return header.index(key)
    ci, di, si, ei, hi = [idx(n) for n in ("CHANNEL", "DATE", "START", "END", "Host_Name")]
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y")
    selected = []
    for row in rows[1:]:
        def cell(i): return str(row[i]).strip() if i < len(row) else ""
        if cell(ci).casefold() == CHANNEL.casefold() and cell(di) == today:
            selected.append({"start": cell(si), "end": cell(ei), "host": cell(hi)})
    print(json.dumps({"status": "DRY_RUN_OK", "date_vn": today, "channel": CHANNEL,
                      "today_sessions": len(selected), "sessions": selected,
                      "writes": 0, "recordings": 0}, ensure_ascii=False))
if __name__ == "__main__":
    main()

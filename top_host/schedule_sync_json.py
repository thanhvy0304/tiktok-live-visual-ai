"""Export today's Top Host sessions to a read-only JSON artifact."""
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo
from google.auth import default
from google.auth.transport.requests import AuthorizedSession

SHEET_ID = '1XWj-zSMcb2W5fPqKT8LptOwSwCFpEQ_4MYl5keIihXE'
SHEET_RANGE = "'LIVE_SCHEDULE'!A1:AZ10000"
CHANNEL = 'Tiktok Tích Xanh'
OUTPUT = Path('top_host/output/schedule_sync.json')


def cell(row, i):
    return str(row[i]).strip() if i is not None and i < len(row) else ''


def main():
    date_vn = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y')
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{quote(SHEET_RANGE, safe="")}'
    response = AuthorizedSession(credentials).get(url, timeout=40)
    if not response.ok:
        raise RuntimeError(f'Sheets read failed: HTTP {response.status_code}')
    rows = response.json().get('values', [])
    if not rows:
        raise RuntimeError('LIVE_SCHEDULE empty')
    headers = [str(x).strip().casefold() for x in rows[0]]

    def idx(name):
        try:
            return headers.index(name.casefold())
        except ValueError:
            raise RuntimeError(f'Missing required column: {name}') from None

    ci, di, si, ei, hi, idi = [idx(n) for n in ('CHANNEL', 'DATE', 'START', 'END', 'Host_Name', 'Schedule_ID')]
    sessions, seen = [], set()
    for row in rows[1:]:
        if cell(row, ci).casefold() != CHANNEL.casefold() or cell(row, di) != date_vn:
            continue
        host = cell(row, hi)
        if not host:
            continue
        schedule_id = cell(row, idi)
        if not schedule_id or schedule_id in seen:
            raise RuntimeError('Missing or duplicate Schedule_ID in matched sessions')
        seen.add(schedule_id)
        sessions.append({'schedule_id': schedule_id, 'host': host, 'channel': CHANNEL,
                         'date_vn': date_vn, 'start': cell(row, si), 'end': cell(row, ei),
                         'selection': 'CHANNEL_ALL_HOSTS'})
    result = {'status': 'TOP_HOST_SCHEDULE_SYNC_OK', 'date_vn': date_vn,
              'timezone': 'Asia/Ho_Chi_Minh', 'channel': CHANNEL,
              'matched_sessions': len(sessions), 'sessions': sessions,
              'writes_to_sheets': 0, 'recordings': 0, 'capture': False}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

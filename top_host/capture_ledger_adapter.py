"""STEP 12: GitHub Contents ledger adapter, offline-only safety tests.

Not invoked by a production workflow. Writing requires explicit activation,
contents:write and a successful real screenshot followed by leader verification.
GitHub SHA conditional writes protect against stale updates, not simultaneous
capture; a separate capture lock is required before production use.
"""
import base64
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LEDGER_PATH = "top_host/state/capture_ledger.json"


def validate_ledger(ledger):
    if not isinstance(ledger, dict) or ledger.get("schema") != 1:
        raise ValueError("Invalid ledger schema")
    entries = ledger.get("completed", {})
    if not isinstance(entries, dict):
        raise ValueError("Invalid completed map")
    for key, value in entries.items():
        if not isinstance(key, str) or len(key) != 24 or not all(c in "0123456789abcdef" for c in key):
            raise ValueError("Invalid capture key")
        if not isinstance(value, dict) or not value.get("evidence_ref") or not value.get("reviewed_by"):
            raise ValueError("Completed capture requires evidence and leader review")
    return ledger


def mark_completed(ledger, key, evidence_ref, reviewed_by):
    validate_ledger(ledger)
    if not evidence_ref or not reviewed_by:
        raise ValueError("Missing evidence or reviewer")
    if len(key) != 24 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("Invalid key")
    entries = dict(ledger["completed"])
    if key in entries:
        raise ValueError("Already completed")
    entries[key] = {"evidence_ref": evidence_ref, "reviewed_by": reviewed_by}
    return {"schema": 1, "completed": entries}


def _request(url, token, method="GET", payload=None):
    headers = {"Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
               "X-GitHub-Api-Version": "2022-11-28"}
    data = None if payload is None else json.dumps(payload).encode()
    if data is not None:
        headers["Content-Type"] = "application/json"
    with urlopen(Request(url, headers=headers, data=data, method=method), timeout=20) as r:
        return json.load(r)


def read_ledger(repo, token):
    url = f"https://api.github.com/repos/{repo}/contents/{LEDGER_PATH}"
    try:
        obj = _request(url, token)
    except HTTPError as e:
        if e.code == 404:
            return {"schema": 1, "completed": {}}, None
        raise
    raw = base64.b64decode(obj["content"]).decode("utf-8")
    return validate_ledger(json.loads(raw)), obj["sha"]


def commit_ledger(repo, token, ledger, sha):
    """Conditional commit; caller must handle 409/422 conflicts by re-reading."""
    validate_ledger(ledger)
    url = f"https://api.github.com/repos/{repo}/contents/{LEDGER_PATH}"
    body = {"message": "Record leader-reviewed Top Host capture",
            "content": base64.b64encode((json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()).decode(),
            "branch": "main"}
    if sha:
        body["sha"] = sha
    return _request(url, token, method="PUT", payload=body)

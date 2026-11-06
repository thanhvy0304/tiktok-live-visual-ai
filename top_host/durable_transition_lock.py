"""STEP 17.3 durable GitHub Contents lease claim (no screenshot).

Requires workflow-level concurrency shared by every future capture workflow.
GitHub Contents conditional SHA updates reject stale writes. This is a lease
claim only, NOT proof of a screenshot or a completed session.
"""
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from top_host.capture_lock_preview import plan_claim

PATH = "top_host/state/transition_leases.json"
OUT = Path("top_host/output/durable_lock_result.json")


def request(url, token, method="GET", payload=None):
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + token,
               "X-GitHub-Api-Version": "2022-11-28"}
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    if data is not None:
        headers["Content-Type"] = "application/json"
    with urlopen(Request(url, headers=headers, data=data, method=method), timeout=20) as response:
        return json.load(response)


def load(repo, token):
    url = f"https://api.github.com/repos/{repo}/contents/{PATH}?ref=main"
    try:
        obj = request(url, token)
    except HTTPError as e:
        if e.code == 404:
            return {"schema": 1, "entries": {}}, None
        raise
    data = json.loads(base64.b64decode(obj["content"]).decode("utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("entries"), dict):
        raise ValueError("Invalid durable lease ledger")
    return data, obj["sha"]


def save(repo, token, data, sha):
    url = f"https://api.github.com/repos/{repo}/contents/{PATH}"
    payload = {"message": "Record Top Host transition lease claim",
               "branch": "main",
               "content": base64.b64encode((json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()).decode()}
    if sha:
        payload["sha"] = sha
    return request(url, token, "PUT", payload)


def claim(decision, data, now, run_id):
    proposal = plan_claim(decision, data["entries"], now, run_id)
    if proposal["status"] != "CLAIM_PROPOSAL_ONLY":
        return proposal, data
    entries = dict(data["entries"])
    entries[proposal["capture_key"]] = {
        "state": "CLAIMED", "run_id": proposal["run_id"],
        "lease_until": proposal["lease_until"],
        "schedule_id": decision["schedule_id"],
        "scheduled_host": decision["scheduled_host"]
    }
    return {"status": "LEASE_CLAIM_READY", "capture_key": proposal["capture_key"],
            "lease_until": proposal["lease_until"]}, {"schema": 1, "entries": entries}


def main():
    decision = json.loads(Path("top_host/output/transition_decision.json").read_text(encoding="utf-8"))
    result = {"status": "SKIP", "reason": "NO_TRANSITION", "capture_started": False}
    if decision.get("status") == "TRANSITION_CANDIDATE":
        token = os.environ["GITHUB_TOKEN"]
        repo = os.environ["GITHUB_REPOSITORY"]
        run_id = os.environ["GITHUB_RUN_ID"]
        data, sha = load(repo, token)
        result, updated = claim(decision, data, datetime.now(timezone.utc), run_id)
        if result["status"] == "LEASE_CLAIM_READY":
            try:
                save(repo, token, updated, sha)
            except HTTPError as e:
                if e.code in (409, 422):
                    result = {"status": "CONFLICT_RETRY_REQUIRED", "capture_started": False}
                else:
                    raise
            else:
                result["status"] = "LEASE_CLAIMED"
        result["capture_started"] = False
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""STEP 16: package an existing capture as evidence, without declaring identity verified.

Artifacts remain in GitHub Actions for limited retention. This is not a durable
capture ledger, nor does it automatically authorize future captures.
"""
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("top_host/output")
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def safe_segment(value):
    value = str(value or "").strip()
    if not value or len(value) > 100 or "/" in value or "\\" in value or value in (".", ".."):
        raise ValueError("Unsafe evidence path segment")
    return re.sub(r"[^\w\- ]", "_", value, flags=re.UNICODE).replace(" ", "_")


def package(capture, image_path, base=ROOT / "evidence"):
    if capture.get("status") != "FRAME_FOR_LEADER_REVIEW" or capture.get("screenshot_count") != 1:
        return {"status": "NO_EVIDENCE", "reason": capture.get("reason", "NO_VALID_FRAME")}
    if capture.get("playback_observed") is not True or capture.get("host_identity_verified") is not False:
        raise ValueError("Invalid capture flags")
    if not image_path.is_file() or image_path.stat().st_size == 0:
        raise ValueError("Missing screenshot")
    stamp = datetime.fromisoformat(capture["generated_at_vn"])
    if stamp.tzinfo is None:
        raise ValueError("Timezone required")
    host = safe_segment(capture["scheduled_host"])
    sid = safe_segment(capture["schedule_id"])
    target = base / stamp.strftime("%Y-%m-%d") / sid / host
    target.mkdir(parents=True, exist_ok=True)
    dest = target / "capture.png"
    shutil.copyfile(image_path, dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    manifest = {
        "schema": 1, "status": "AWAITING_LEADER_REVIEW",
        "scheduled_host": capture["scheduled_host"],
        "channel": "Tiktok Tích Xanh", "schedule_id": capture["schedule_id"],
        "captured_at_vn": stamp.isoformat(),
        "image_file": "capture.png", "image_sha256": digest,
        "identity_verified": False, "reviewer": None,
        "reviewed_at_vn": None,
        "note": "Leader must confirm actual host; schedule alone is not proof."
    }
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "PACKAGED_FOR_REVIEW", "evidence_path": str(target),
            "image_sha256": digest, "identity_verified": False}


def main():
    capture = json.loads((ROOT / "leader_review.json").read_text(encoding="utf-8"))
    result = package(capture, ROOT / "leader_review_frame.png")
    (ROOT / "evidence_package_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

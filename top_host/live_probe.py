"""STEP 08: read-only TikTok LIVE playback probe driven by validated schedule handoff."""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

INPUT = Path("top_host/output/capture_handoff.json")
OUTPUT = Path("top_host/output/live_probe.json")
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
ALLOWED_URL = "https://www.tiktok.com/@hannaholala/live"


async def probe(url):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(6000)
            video = page.locator("video").first
            if await video.count() == 0:
                return {"playback_observed": False, "reason": "NO_VIDEO_ELEMENT",
                        "http_status": response.status if response else None}
            first = await video.evaluate("""v => ({readyState:v.readyState,width:v.videoWidth,height:v.videoHeight,time:v.currentTime})""")
            await page.wait_for_timeout(3000)
            second = await video.evaluate("""v => ({readyState:v.readyState,width:v.videoWidth,height:v.videoHeight,time:v.currentTime})""")
            playing = (second["readyState"] >= 2 and second["width"] > 0
                       and second["height"] > 0 and second["time"] > first["time"])
            return {"playback_observed": bool(playing), "reason": "VIDEO_PROGRESS" if playing else "NO_VIDEO_PROGRESS",
                    "http_status": response.status if response else None}
        finally:
            await browser.close()


async def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    now = datetime.now(TZ)
    if data.get("status") != "CAPTURE_HANDOFF_PREVIEW_OK":
        raise ValueError("Invalid handoff status")
    if data.get("date_vn") != now.strftime("%d/%m/%Y"):
        raise ValueError("Stale handoff")
    if data.get("writes_to_sheets") != 0 or data.get("recordings") != 0 or data.get("capture_started") is not False:
        raise ValueError("Unsafe handoff flags")
    results = []
    for item in data.get("sessions", []):
        if item.get("live_url") != ALLOWED_URL or item.get("channel") != "Tiktok Tích Xanh":
            raise ValueError("Unexpected LIVE target")
        if not item.get("host", "").strip():
            raise ValueError("Unexpected host")
        start = datetime.fromisoformat(item["start_vn"])
        end = datetime.fromisoformat(item["end_vn"])
        active = start <= now < end
        result = {"schedule_id": item["schedule_id"], "scheduled_host": item["host"],
                  "scheduled_active": active, "live_url": ALLOWED_URL,
                  "host_identity_verified": False, "capture_started": False}
        if active:
            try:
                result.update(await probe(ALLOWED_URL))
            except Exception as exc:
                result.update({"playback_observed": False, "reason": "PROBE_ERROR",
                               "error_type": type(exc).__name__})
        else:
            result.update({"playback_observed": False, "reason": "OUTSIDE_SCHEDULE_WINDOW"})
        results.append(result)
    output = {"status": "LIVE_PROBE_COMPLETE", "generated_at_vn": now.isoformat(),
              "sessions": results, "writes_to_sheets": 0, "recordings": 0,
              "screenshots": 0, "capture_started": False,
              "note": "Video playback does not verify host identity. No capture performed."}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

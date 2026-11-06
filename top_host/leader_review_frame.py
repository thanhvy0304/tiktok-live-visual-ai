"""STEP 09: manual read-only single-frame evidence, never assert host identity."""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

ROOT = Path("top_host/output")
URL = "https://www.tiktok.com/@hannaholala/live"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


async def main():
    handoff = json.loads((ROOT / "capture_handoff.json").read_text(encoding="utf-8"))
    now = datetime.now(TZ)
    if handoff.get("status") != "CAPTURE_HANDOFF_PREVIEW_OK" or handoff.get("date_vn") != now.strftime("%d/%m/%Y"):
        raise ValueError("Invalid or stale handoff")
    if handoff.get("writes_to_sheets") != 0 or handoff.get("recordings") != 0 or handoff.get("capture_started") is not False:
        raise ValueError("Unsafe handoff")
    result = {"status": "NOT_CAPTURED", "generated_at_vn": now.isoformat(),
              "host_identity_verified": False, "recordings": 0, "writes_to_sheets": 0,
              "screenshot_count": 0, "note": "Manual leader review required for host identity."}
    active = [s for s in handoff.get("sessions", [])
              if datetime.fromisoformat(s["start_vn"]) <= now < datetime.fromisoformat(s["end_vn"])]
    if len(active) != 1:
        result["reason"] = "NO_UNIQUE_ACTIVE_SESSION"
    else:
        session = active[0]
        if session.get("host", "").strip().casefold() != "thanh huyền" or session.get("channel") != "Tiktok Tích Xanh" or session.get("live_url") != URL:
            raise ValueError("Unexpected session")
        result["schedule_id"] = session["schedule_id"]
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = await browser.new_page(viewport={"width": 1280, "height": 900})
                await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(6000)
                video = page.locator("video").first
                if await video.count() == 0:
                    result["reason"] = "NO_VIDEO_ELEMENT"
                else:
                    first = await video.evaluate("v => ({t:v.currentTime,ready:v.readyState,w:v.videoWidth,h:v.videoHeight})")
                    await page.wait_for_timeout(3000)
                    second = await video.evaluate("v => ({t:v.currentTime,ready:v.readyState,w:v.videoWidth,h:v.videoHeight})")
                    if second["ready"] >= 2 and second["w"] > 0 and second["h"] > 0 and second["t"] > first["t"]:
                        await video.screenshot(path=str(ROOT / "leader_review_frame.png"))
                        result.update(status="FRAME_FOR_LEADER_REVIEW", reason="VIDEO_PROGRESS",
                                      screenshot_count=1, playback_observed=True)
                    else:
                        result["reason"] = "NO_VIDEO_PROGRESS"
            except Exception as exc:
                result.update(reason="PROBE_ERROR", error_type=type(exc).__name__)
            finally:
                await browser.close()
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "leader_review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())


"""
TIKTOK LIVE VISUAL AI
FILE: capture_by_schedule.py
VERSION: 1.0 - PILOT

Chức năng:
- Kết nối Apps Script API
- Đọc các ca Host vừa bắt đầu
- Chụp screenshot TikTok LIVE bằng Playwright
- Lưu screenshot dưới dạng GitHub Artifact

Chưa ghi Google Sheets / Google Drive.
Chưa có chống trùng bền vững.
Chưa chạy định kỳ.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.async_api import async_playwright


API_URL = os.environ.get("VISUAL_API_URL", "").strip()
API_TOKEN = os.environ.get("VISUAL_API_TOKEN", "").strip()

OUTPUT_DIR = Path("visual_captures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_due_sessions():
    """Lấy các ca vừa bắt đầu từ Apps Script."""

    if not API_URL or not API_TOKEN:
        raise RuntimeError("Missing API configuration")

    payload = json.dumps({
        "token": API_TOKEN,
        "action": "due"
    }).encode("utf-8")

    request = Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("ok") is not True:
        raise RuntimeError(
            "API request failed: " + str(data.get("error"))
        )

    return data.get("sessions", [])


async def capture_session(page, session):
    """Chụp một screenshot của ca Host."""

    schedule_id = session.get("schedule_id", "")
    host_name = session.get("host_name", "Unknown")
    live_url = session.get("live_url", "")

    if not live_url.startswith("https://www.tiktok.com/"):
        raise ValueError("Invalid TikTok LIVE URL")

    print("Schedule:", schedule_id)
    print("Host:", host_name)

    response = await page.goto(
        live_url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    await page.wait_for_timeout(15000)

    video = page.locator("video").first

    if await video.count() == 0:
        print("No video element; skipping capture")
        return

    state = await video.evaluate(
        """v => ({
            readyState: v.readyState,
            videoWidth: v.videoWidth,
            videoHeight: v.videoHeight
        })"""
    )

    if (
        state["readyState"] < 2
        or state["videoWidth"] <= 0
        or state["videoHeight"] <= 0
    ):
        print("Video is not ready; skipping capture")
        return

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    safe_id = "".join(
        c for c in schedule_id if c.isalnum() or c in "-_"
    ) or "UNKNOWN"

    image_path = OUTPUT_DIR / f"{safe_id}_{timestamp}.png"

    await page.screenshot(
        path=str(image_path),
        full_page=False
    )

    print("Screenshot saved:", image_path)


async def main():
    sessions = get_due_sessions()

    print("Due sessions:", len(sessions))

    if not sessions:
        print("No sessions require capture.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        try:
            page = await browser.new_page(
                viewport={"width": 1280, "height": 900},
                device_scale_factor=1
            )

            for session in sessions:
                try:
                    await capture_session(page, session)
                except Exception as error:
                    print("Capture failed:", type(error).__name__)
                    raise

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

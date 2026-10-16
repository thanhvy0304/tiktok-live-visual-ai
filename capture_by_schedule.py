
"""
TIKTOK LIVE VISUAL AI
FILE: capture_by_schedule.py
VERSION: 1.1 - MANUAL TEST MODE

- NORMAL: Chụp các ca vừa bắt đầu
- TEST: Chọn một Schedule_ID của ngày hiện tại
- Không ghi Google Sheets
- Không thay đổi lịch Host
- Không bật tự động định kỳ
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

TEST_MODE = os.environ.get(
    "TEST_MODE", "false"
).lower() == "true"

TEST_SCHEDULE_ID = os.environ.get(
    "TEST_SCHEDULE_ID", ""
).strip()

OUTPUT_DIR = Path("visual_captures")


def get_sessions(action):
    if not API_URL.startswith("https://"):
        raise RuntimeError("Invalid API URL")

    if not API_TOKEN:
        raise RuntimeError("Missing API token")

    payload = json.dumps({
        "token": API_TOKEN,
        "action": action
    }).encode("utf-8")

    request = Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urlopen(request, timeout=45) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if result.get("ok") is not True:
        raise RuntimeError(
            "API error: " + str(result.get("error"))
        )

    return result.get("sessions", [])


async def capture_session(page, session):
    schedule_id = session.get("schedule_id", "")
    live_url = session.get("live_url", "")

    if not (
        live_url == "https://www.tiktok.com/@hannahteam.review/live"
    ):
        raise ValueError("Unexpected LIVE URL")

    print("Schedule_ID:", schedule_id)
    print("Scheduled Host:", session.get("host_name"))

    await page.goto(
        live_url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    await page.wait_for_timeout(15000)

    video = page.locator("video").first

    if await video.count() == 0:
        raise RuntimeError("No video element found")

    first = await video.evaluate(
        """v => ({
            readyState: v.readyState,
            width: v.videoWidth,
            height: v.videoHeight,
            currentTime: v.currentTime
        })"""
    )

    await page.wait_for_timeout(3000)

    second = await video.evaluate(
        """v => ({
            readyState: v.readyState,
            width: v.videoWidth,
            height: v.videoHeight,
            currentTime: v.currentTime
        })"""
    )

    if (
        second["readyState"] < 2
        or second["width"] <= 0
        or second["height"] <= 0
        or second["currentTime"] <= first["currentTime"]
    ):
        raise RuntimeError("Video playback not confirmed")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    safe_id = "".join(
        c for c in schedule_id
        if c.isalnum() or c in "-_"
    ) or "UNKNOWN"

    filename = OUTPUT_DIR / (
        f"TEST_{safe_id}_{timestamp}.png"
        if TEST_MODE else
        f"{safe_id}_{timestamp}.png"
    )

    await page.screenshot(
        path=str(filename),
        full_page=False
    )

    print("Screenshot saved:", filename)


async def main():
    action = "today" if TEST_MODE else "due"

    sessions = get_sessions(action)

    if TEST_MODE:
        if not TEST_SCHEDULE_ID:
            raise RuntimeError(
                "TEST_SCHEDULE_ID is required"
            )

        sessions = [
            s for s in sessions
            if s.get("schedule_id") == TEST_SCHEDULE_ID
        ]

        if len(sessions) != 1:
            raise RuntimeError(
                "Schedule_ID not found or not unique "
                "in today's schedule"
            )

        print("TEST MODE ENABLED")
    else:
        print("NORMAL MODE")

    print("Selected sessions:", len(sessions))

    if not sessions:
        print("No sessions require capture")
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
                await capture_session(page, session)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

LIVE_URL = "https://www.tiktok.com/@hannahteam.review/live"
OUTPUT_DIR = Path("screenshots")


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1
        )

        try:
            print(f"Opening: {LIVE_URL}")

            response = await page.goto(
                LIVE_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print(
                "HTTP status:",
                response.status if response else "Unknown"
            )

            await page.wait_for_timeout(15000)

            print("Current URL:", page.url)
            print("Page title:", await page.title())

            video_count = await page.locator("video").count()
            print("Video elements:", video_count)

            if video_count:
                video_status = await page.locator("video").first.evaluate(
                    """v => ({
                        readyState: v.readyState,
                        videoWidth: v.videoWidth,
                        videoHeight: v.videoHeight,
                        currentTime: v.currentTime,
                        paused: v.paused
                    })"""
                )
                print("Video status:", video_status)

            timestamp = datetime.now(timezone.utc).strftime(
                "%Y%m%d_%H%M%S"
            )
            output = OUTPUT_DIR / f"tiktok_live_{timestamp}.png"

            await page.screenshot(
                path=str(output),
                full_page=False
            )

            print(f"Screenshot saved: {output}")

        except Exception as error:
            print(f"Test failed: {error}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


import json
import subprocess
import sys
from pathlib import Path

import yt_dlp

LIVE_URL = "https://www.tiktok.com/@hannahteam.review/live"
OUTPUT_DIR = Path("audio_qc_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    result = {
        "live_url": LIVE_URL,
        "status": "FAILED",
        "audio_file": None,
        "error": None,
    }

    try:
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }) as ydl:
            info = ydl.extract_info(LIVE_URL, download=False)

        formats = info.get("formats") or []
        candidates = [
            f for f in formats
            if f.get("url") and f.get("acodec") != "none"
        ]

        stream_url = (
            candidates[-1]["url"]
            if candidates
            else info.get("url")
        )

        if not stream_url:
            raise RuntimeError("Không tìm được audio stream URL")

        output_file = OUTPUT_DIR / "live_audio_20s.wav"

        command = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-i", stream_url,
            "-t", "20",
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(output_file),
        ]

        subprocess.run(
            command,
            check=True,
            timeout=90,
            capture_output=True,
            text=True,
        )

        if not output_file.exists() or output_file.stat().st_size == 0:
            raise RuntimeError("Audio file rỗng")

        result["status"] = "CAPTURED_UNVERIFIED"
        result["audio_file"] = str(output_file)
        result["bytes"] = output_file.stat().st_size

    except Exception as exc:
        result["error"] = str(exc)

    finally:
        (OUTPUT_DIR / "probe_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] != "CAPTURED_UNVERIFIED":
        sys.exit(1)


if __name__ == "__main__":
    main()

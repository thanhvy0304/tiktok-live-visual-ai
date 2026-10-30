
import json
import re
import subprocess
import sys
from pathlib import Path

import yt_dlp

LIVE_URL = "https://www.tiktok.com/@hannahteam.review/live"

OUTPUT_DIR = Path("audio_qc_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_FILE = OUTPUT_DIR / "live_audio_20s.wav"
RESULT_FILE = OUTPUT_DIR / "probe_result.json"
LOG_FILE = OUTPUT_DIR / "ffmpeg_diagnostic.log"


def sanitize(text):
    """Remove signed URLs and possible credentials from logs."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")

    text = text or ""

    text = re.sub(
        r"https?://[^\s\"'<>]+",
        "[STREAM_URL_REDACTED]",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"(?i)(authorization|cookie|token|signature|sessionid)"
        r"\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        text,
    )

    return text[-6000:]


def save_log(message):
    LOG_FILE.write_text(
        sanitize(message),
        encoding="utf-8",
    )


def duration_seconds(path):
    p = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )

    return float(p.stdout.strip())


def main():
    result = {
        "live_url": LIVE_URL,
        "status": "FAILED",
        "stage": "extract",
        "audio_file": None,
        "error": None,
    }

    try:
        print("STAGE 1: Extract LIVE stream")

        with yt_dlp.YoutubeDL({
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": 15,
        }) as ydl:
            info = ydl.extract_info(
                LIVE_URL,
                download=False,
            )

        if not info:
            raise RuntimeError(
                "TikTok không trả thông tin LIVE"
            )

        formats = info.get("formats") or []

        candidates = [
            f for f in formats
            if f.get("url")
            and f.get("acodec") != "none"
        ]

        candidates.sort(
            key=lambda f: (
                f.get("protocol") in ("m3u8", "m3u8_native"),
                f.get("abr") or 0,
            ),
            reverse=True,
        )

        stream_url = (
            candidates[0]["url"]
            if candidates
            else info.get("url")
        )

        if not stream_url:
            raise RuntimeError(
                "Không tìm thấy audio stream"
            )

        result["stage"] = "capture"

        print("STAGE 2: Capture 20 seconds")

        command = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-y",
            "-loglevel", "error",
            "-rw_timeout", "10000000",
            "-i", stream_url,
            "-t", "20",
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(AUDIO_FILE),
        ]

        try:
            p = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=65,
            )

            save_log(
                "FFMPEG_EXIT_CODE: "
                + str(p.returncode)
                + "\n\n"
                + (p.stderr or "NO_STDERR_OUTPUT")
            )

            result["ffmpeg_exit_code"] = p.returncode

            if p.returncode != 0:
                raise RuntimeError(
                    "FFmpeg failed; inspect diagnostic log"
                )

        except subprocess.TimeoutExpired as exc:
            save_log(
                "FFMPEG_TIMEOUT_65S\n\n"
                + sanitize(exc.stderr)
            )

            raise RuntimeError(
                "FFmpeg timeout after 65 seconds"
            ) from None

        result["stage"] = "validate"

        print("STAGE 3: Validate audio")

        if not AUDIO_FILE.exists():
            raise RuntimeError(
                "Audio file not created"
            )

        if AUDIO_FILE.stat().st_size < 32000:
            raise RuntimeError(
                "Audio file too small"
            )

        duration = duration_seconds(AUDIO_FILE)

        result["duration_seconds"] = round(
            duration, 2
        )
        result["bytes"] = AUDIO_FILE.stat().st_size

        if duration < 10:
            raise RuntimeError(
                "Audio duration below 10 seconds"
            )

        result["audio_file"] = str(AUDIO_FILE)
        result["status"] = "CAPTURED_UNVERIFIED"
        result["stage"] = "complete"

        print("AUDIO CAPTURED - MANUAL REVIEW REQUIRED")

    except Exception as exc:
        result["error"] = sanitize(str(exc))
        print(
            "ERROR TYPE:",
            type(exc).__name__,
        )

    finally:
        RESULT_FILE.write_text(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

    return (
        0
        if result["status"] == "CAPTURED_UNVERIFIED"
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())

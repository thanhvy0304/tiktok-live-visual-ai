import json
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


def duration_seconds(path):
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=15, check=True,
    )
    return float(p.stdout.strip())


def main():
    result = {"live_url": LIVE_URL, "status": "FAILED", "stage": "extract",
              "audio_file": None, "error": None}
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                               "skip_download": True, "socket_timeout": 15}) as ydl:
            info = ydl.extract_info(LIVE_URL, download=False)
        if not info:
            raise RuntimeError("TikTok không trả thông tin LIVE")
        formats = info.get("formats") or []
        candidates = [f for f in formats if f.get("url") and f.get("acodec") != "none"]
        candidates.sort(key=lambda f: (f.get("protocol") in ("m3u8", "m3u8_native"),
                                       f.get("abr") or 0), reverse=True)
        stream_url = candidates[0]["url"] if candidates else info.get("url")
        if not stream_url:
            raise RuntimeError("Không tìm thấy URL luồng có audio")
        result["stage"] = "capture"
        command = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "warning",
                   "-rw_timeout", "10000000", "-i", stream_url,
                   "-t", "20", "-vn", "-ac", "1", "-ar", "16000",
                   "-c:a", "pcm_s16le", str(AUDIO_FILE)]
        try:
            p = subprocess.run(command, capture_output=True, text=True, timeout=65)
            # Never persist raw stderr: signed stream URLs may contain access tokens.
            LOG_FILE.write_text("FFmpeg exit code: " + str(p.returncode) + "\n", encoding="utf-8")
            if p.returncode != 0:
                raise RuntimeError("FFmpeg không hoàn thành (exit " + str(p.returncode) + ")")
        except subprocess.TimeoutExpired:
            LOG_FILE.write_text("FFmpeg timeout after 65 seconds\n", encoding="utf-8")
            raise RuntimeError("FFmpeg timeout sau 65 giây") from None
        result["stage"] = "validate"
        if not AUDIO_FILE.exists() or AUDIO_FILE.stat().st_size < 32000:
            raise RuntimeError("File audio thiếu hoặc quá nhỏ")
        duration = duration_seconds(AUDIO_FILE)
        result["duration_seconds"] = round(duration, 2)
        result["bytes"] = AUDIO_FILE.stat().st_size
        if duration < 10:
            raise RuntimeError("Audio ngắn hơn 10 giây")
        result["audio_file"] = str(AUDIO_FILE)
        result["status"] = "CAPTURED_UNVERIFIED"
        result["stage"] = "complete"
    except Exception as exc:
        # Error strings from external libraries can include signed URLs.
        result["error"] = type(exc).__name__ + " at stage " + result["stage"]
        if isinstance(exc, RuntimeError):
            result["error"] = str(exc)
    finally:
        RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "CAPTURED_UNVERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())

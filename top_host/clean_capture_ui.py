"""Conservative TikTok UI cleanup for manual screenshot evidence.

Dismiss visible tutorial buttons only. Geometry-based gate distinguishes small
login controls from a modal obscuring the video. No auth bypass or DOM removal.
"""
import re

TUTORIAL_LABELS = (re.compile(r"^got it$", re.I), re.compile(r"^understood$", re.I))


def classify_overlay(text):
    label = " ".join(str(text or "").split()).casefold()
    if any(p.fullmatch(label) for p in TUTORIAL_LABELS):
        return "TUTORIAL_DISMISSIBLE"
    if any(s in label for s in ("log in", "login", "sign in", "đăng nhập")):
        return "AUTH_REQUIRED"
    return "OTHER"


async def cleanup_tutorial(page):
    clicked = 0
    for label in ("Got it", "Understood"):
        button = page.get_by_role("button", name=re.compile(r"^" + re.escape(label) + r"$", re.I))
        try:
            if await button.count() == 1 and await button.is_visible():
                await button.click(timeout=2000)
                clicked += 1
        except Exception:
            pass
    return {"tutorial_buttons_dismissed": clicked}


async def overlay_gate(page, video):
    """Inspect visible UI intersection with video, without modifying the page."""
    return await video.evaluate("""v => {
      const r = v.getBoundingClientRect();
      const area = Math.max(1, r.width * r.height);
      const selectors = 'button,[role="dialog"],[aria-modal="true"]';
      const hits = [...document.querySelectorAll(selectors)].filter(el => {
        const s = getComputedStyle(el), b = el.getBoundingClientRect();
        return s.visibility !== 'hidden' && s.display !== 'none' &&
          b.width > 0 && b.height > 0 &&
          b.left < r.right && b.right > r.left && b.top < r.bottom && b.bottom > r.top;
      }).map(el => {
        const b = el.getBoundingClientRect();
        const width = Math.max(0, Math.min(r.right, b.right) - Math.max(r.left, b.left));
        const height = Math.max(0, Math.min(r.bottom, b.bottom) - Math.max(r.top, b.top));
        return {
          text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0,120),
          overlap_ratio: (width * height) / area,
          is_modal: el.matches('[role="dialog"],[aria-modal="true"]')
        };
      });
      return {overlays: hits, video_visible: r.width > 0 && r.height > 0};
    }""")


def assess_overlay(gate):
    if not gate.get("video_visible"):
        return "VIDEO_NOT_VISIBLE"
    overlays = gate.get("overlays")
    if not isinstance(overlays, list):
        # Old format has no geometry; fail closed rather than silently bypassing.
        return "OVERLAY_GEOMETRY_UNAVAILABLE"
    for item in overlays:
        if not isinstance(item, dict):
            return "OVERLAY_GEOMETRY_UNAVAILABLE"
        ratio = item.get("overlap_ratio")
        if not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1:
            return "OVERLAY_GEOMETRY_UNAVAILABLE"
        kind = classify_overlay(item.get("text", ""))
        if kind == "AUTH_REQUIRED" and (item.get("is_modal") or ratio >= 0.20):
            return "AUTH_OVERLAY_PRESENT"
        if kind == "TUTORIAL_DISMISSIBLE" and ratio >= 0.10:
            return "TUTORIAL_OVERLAY_PRESENT"
        if item.get("is_modal") and ratio >= 0.20:
            return "MODAL_OVER_VIDEO"
    return "NO_KNOWN_BLOCKING_OVERLAY"

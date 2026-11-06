"""Conservative TikTok UI cleanup for manual screenshot evidence.

Only dismiss a visible non-auth tutorial button. Never remove DOM overlays,
bypass login, or treat clean UI as verified host identity.
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
    """Detect visible text overlays crossing video; fail closed if uncertain."""
    return await video.evaluate("""v => {
      const r = v.getBoundingClientRect();
      const elements = [...document.querySelectorAll('button,[role="dialog"],[aria-modal="true"]')];
      const hits = elements.filter(el => {
        const s = getComputedStyle(el), b = el.getBoundingClientRect();
        return s.visibility !== 'hidden' && s.display !== 'none' &&
          b.width > 0 && b.height > 0 &&
          b.left < r.right && b.right > r.left && b.top < r.bottom && b.bottom > r.top;
      }).map(el => (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0,120));
      return {overlay_texts: hits, video_visible: r.width > 0 && r.height > 0};
    }""")


def assess_overlay(gate):
    if not gate.get("video_visible"):
        return "VIDEO_NOT_VISIBLE"
    labels = gate.get("overlay_texts", [])
    if any(classify_overlay(x) == "AUTH_REQUIRED" for x in labels):
        return "AUTH_OVERLAY_PRESENT"
    if any(classify_overlay(x) == "TUTORIAL_DISMISSIBLE" for x in labels):
        return "TUTORIAL_OVERLAY_PRESENT"
    # Other buttons can be native TikTok controls, so do not falsely call them blockers.
    return "NO_KNOWN_BLOCKING_OVERLAY"

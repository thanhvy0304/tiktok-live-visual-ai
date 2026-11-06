import unittest
from top_host.clean_capture_ui import classify_overlay, assess_overlay

def gate(text, ratio, modal=False):
    return {"video_visible": True, "overlays": [
        {"text": text, "overlap_ratio": ratio, "is_modal": modal}
    ]}

class CleanCaptureTests(unittest.TestCase):
    def test_tutorial(self):
        self.assertEqual(classify_overlay("Got it"), "TUTORIAL_DISMISSIBLE")
    def test_auth(self):
        self.assertEqual(classify_overlay("Log in"), "AUTH_REQUIRED")
    def test_small_login_button_allowed(self):
        self.assertEqual(assess_overlay(gate("Log in", 0.01)), "NO_KNOWN_BLOCKING_OVERLAY")
    def test_large_login_overlay_blocks(self):
        self.assertEqual(assess_overlay(gate("Log in", 0.35)), "AUTH_OVERLAY_PRESENT")
    def test_modal_login_blocks_even_if_small(self):
        self.assertEqual(assess_overlay(gate("Log in", 0.05, True)), "AUTH_OVERLAY_PRESENT")
    def test_tutorial_blocks(self):
        self.assertEqual(assess_overlay(gate("Got it", 0.2)), "TUTORIAL_OVERLAY_PRESENT")
    def test_generic_modal_blocks(self):
        self.assertEqual(assess_overlay(gate("Continue", 0.4, True)), "MODAL_OVER_VIDEO")
    def test_video_hidden(self):
        self.assertEqual(assess_overlay({"video_visible": False, "overlays": []}), "VIDEO_NOT_VISIBLE")
    def test_normal_controls_allowed(self):
        self.assertEqual(assess_overlay(gate("Follow", 0.02)), "NO_KNOWN_BLOCKING_OVERLAY")
    def test_legacy_geometry_fails_closed(self):
        self.assertEqual(assess_overlay({"video_visible": True, "overlay_texts": ["Log in"]}), "OVERLAY_GEOMETRY_UNAVAILABLE")

if __name__ == "__main__":
    unittest.main()

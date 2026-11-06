import unittest
from top_host.clean_capture_ui import classify_overlay, assess_overlay

class CleanCaptureTests(unittest.TestCase):
    def test_tutorial(self):
        self.assertEqual(classify_overlay("Got it"), "TUTORIAL_DISMISSIBLE")
    def test_auth(self):
        self.assertEqual(classify_overlay("Log in"), "AUTH_REQUIRED")
    def test_non_tutorial(self):
        self.assertEqual(classify_overlay("Follow"), "OTHER")
    def test_auth_blocks(self):
        self.assertEqual(assess_overlay({"video_visible": True, "overlay_texts": ["Log in"]}), "AUTH_OVERLAY_PRESENT")
    def test_tutorial_blocks(self):
        self.assertEqual(assess_overlay({"video_visible": True, "overlay_texts": ["Got it"]}), "TUTORIAL_OVERLAY_PRESENT")
    def test_video_hidden(self):
        self.assertEqual(assess_overlay({"video_visible": False, "overlay_texts": []}), "VIDEO_NOT_VISIBLE")
    def test_normal_controls_allowed(self):
        self.assertEqual(assess_overlay({"video_visible": True, "overlay_texts": ["Follow"]}), "NO_KNOWN_BLOCKING_OVERLAY")

if __name__ == "__main__":
    unittest.main()

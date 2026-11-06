import json
import tempfile
import unittest
from pathlib import Path
from top_host.evidence_package import package, safe_segment

def capture():
    return {"status": "FRAME_FOR_LEADER_REVIEW", "screenshot_count": 1,
            "playback_observed": True, "host_identity_verified": False,
            "scheduled_host": "Ánh Ly", "schedule_id": "SCH-123",
            "generated_at_vn": "2026-11-06T15:18:00+07:00"}

class EvidenceTests(unittest.TestCase):
    def test_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "frame.png"
            image.write_bytes(b"sample-test-frame")
            result = package(capture(), image, root / "evidence")
            self.assertEqual(result["status"], "PACKAGED_FOR_REVIEW")
            manifest = json.loads((Path(result["evidence_path"]) / "manifest.json").read_text())
            self.assertFalse(manifest["identity_verified"])
            self.assertEqual(manifest["scheduled_host"], "Ánh Ly")
    def test_no_frame(self):
        c = capture(); c["status"] = "NOT_CAPTURED"; c["screenshot_count"] = 0
        self.assertEqual(package(c, Path("missing.png"))["status"], "NO_EVIDENCE")
    def test_missing_image(self):
        with self.assertRaises(ValueError):
            package(capture(), Path("missing.png"))
    def test_path_traversal(self):
        with self.assertRaises(ValueError):
            safe_segment("../other")
    def test_no_auto_verified(self):
        c = capture(); c["host_identity_verified"] = True
        with self.assertRaises(ValueError):
            package(c, Path("missing.png"))

if __name__ == "__main__":
    unittest.main()

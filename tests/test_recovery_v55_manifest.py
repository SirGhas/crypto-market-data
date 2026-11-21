"""Manifest must be reproducible and fail closed on report/guard divergence."""
import json
import tempfile
import unittest
from pathlib import Path
from engine_manifest import build_manifest, FILES, ROOT


class ManifestContract(unittest.TestCase):
    def test_snapshot_is_auditable(self):
        result = build_manifest()
        self.assertEqual(result["status"], "PASS", result["findings"])
        self.assertEqual(set(result["files"]), set(FILES))
        self.assertEqual(len(result["files"]["screen"]["sha256"]), 64)
        self.assertIn("not_trade_authorization", result["purpose"])

    def test_repeated_generation_is_identical(self):
        self.assertEqual(build_manifest(), build_manifest())

    def test_guard_score_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for relative in FILES.values():
                dest = base / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / relative).read_bytes())
            path = base / FILES["guard"]
            guard = json.loads(path.read_text())
            first = next(iter(guard["coins"]))
            guard["coins"][first]["score"] = -999
            path.write_text(json.dumps(guard))
            result = build_manifest(base)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("SCORE_GUARD_MISMATCH:" + first, result["findings"])

    def test_invalid_report_timestamp_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for relative in FILES.values():
                dest = base / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / relative).read_bytes())
            path = base / FILES["screen"]
            payload = json.loads(path.read_text())
            payload["generated_at_utc"] = "invalid"
            path.write_text(json.dumps(payload))
            self.assertIn("INVALID_TIMESTAMP:screen", build_manifest(base)["findings"])


if __name__ == "__main__":
    unittest.main()

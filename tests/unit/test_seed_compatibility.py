"""FEAT-030: valid bytes and historical load evidence are distinct capabilities."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog import seed_compatibility as compatibility


class SeedCompatibility(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(bridge, "ROOT", self.root))
        self.seed = self.root / "seed.prt.1"
        self.seed.write_bytes(b"isolated test bytes, never loaded by Creo")
        self.digest = hashlib.sha256(self.seed.read_bytes()).hexdigest()
        self.entry = {"sha256": self.digest, "tested_creo": "10.0.0.0"}
        self.request = {
            "loft_seed": {"snapshot_sha256": self.digest},
            "template_file": str(self.seed),
        }
        self.result = {
            "seed_native_load": {"status": "loaded", "toolkit_code": 0},
            "creo_release_numeric": 44,
            "creo_release_query_code": 0,
            "session_fingerprint": "isolated-session",
            "success": True,
            "saved_file_reloaded_and_verified": True,
        }

    def test_tested_version_is_not_production_version_or_current_compatibility(self):
        value = compatibility.metadata(self.entry)
        self.assertIsNone(value["seed_build_version"])
        self.assertEqual(value["native_compatibility"]["observations"], [])
        self.assertEqual(
            value["native_compatibility"]["status"], "not_verified_for_current_session"
        )

    def test_success_record_is_bound_to_exact_bytes_runtime_and_job(self):
        value = compatibility.observe_load(self.request, self.result, "a" * 32)
        self.assertTrue(value["evidence_persisted"])
        row = compatibility.metadata(self.entry)["native_compatibility"]["observations"][0]
        self.assertEqual(row["seed_sha256"], self.digest)
        self.assertEqual(row["creo_release_numeric"], 44)
        self.assertEqual(row["job_id"], "a" * 32)
        self.assertEqual(
            compatibility.metadata({"sha256": "b" * 64})["native_compatibility"]["observations"], []
        )

    def test_load_failure_does_not_infer_unsupported_creo_version(self):
        self.result["seed_native_load"] = {"status": "load_failed", "toolkit_code": -16}
        self.result["saved_file_reloaded_and_verified"] = False
        value = compatibility.observe_load(self.request, self.result, "a" * 32)
        self.assertEqual(value["toolkit_code"], -16)
        self.assertEqual(value["status"], "load_failed")
        self.assertFalse(value["modeling_saved_reloaded_verified"])

    def test_incomplete_runtime_or_load_attempt_does_not_record_compatibility(self):
        for key, value in (
            ("creo_release_numeric", None),
            ("session_fingerprint", None),
            ("seed_native_load", {"status": "not_attempted"}),
        ):
            with self.subTest(key=key):
                result = {**self.result, key: value}
                observed = compatibility.observe_load(self.request, result, "a" * 32)
                self.assertFalse(observed["evidence_persisted"])
        self.assertFalse((self.root / "build").exists())

    def test_changed_snapshot_or_diagnostic_write_failure_does_not_change_model_success(self):
        self.seed.write_bytes(b"changed snapshot")
        observed = compatibility.observe_load(self.request, self.result, "a" * 32)
        self.assertFalse(observed["evidence_persisted"])
        self.assertIn("changed", observed["evidence_error"])
        self.seed.write_bytes(b"isolated test bytes, never loaded by Creo")
        with patch.object(
            bridge, "write_json", side_effect=OSError("diagnostic storage unavailable")
        ):
            observed = compatibility.observe_load(self.request, self.result, "a" * 32)
        self.assertFalse(observed["evidence_persisted"])
        self.assertTrue(self.result["success"])

    def test_query_drops_unbounded_diagnostic_content(self):
        import json

        folder = self.root / "build/seed_compatibility" / self.digest
        folder.mkdir(parents=True)
        (folder / "untrusted.json").write_text(
            json.dumps(
                {
                    "seed_sha256": self.digest,
                    "status": "loaded",
                    "session_fingerprint": "x" * 4000,
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(
            compatibility.metadata(self.entry)["native_compatibility"]["observations"], []
        )

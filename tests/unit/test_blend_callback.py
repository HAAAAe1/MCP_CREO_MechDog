"""Resident callback artifacts are immutable and never grant loader permission."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from creo_mechdog.blend_callback import callback_setup_status, prepare_callback


class BlendCallbackSetupTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.build = Path(self.workspace.name) / "build"
        self.build.mkdir()
        self.dll = self.build / "creo_blend_sync.dll"
        self.dll.write_bytes(b"fixture callback")
        self.digest = hashlib.sha256(self.dll.read_bytes()).hexdigest()

    def test_verified_build_creates_setup_with_no_authorization_or_ready_claim(self):
        result = prepare_callback(self.build, self.digest)
        self.assertEqual(Path(result["module_file"]).read_bytes(), self.dll.read_bytes())
        self.assertEqual(result["protocol"], 2)
        self.assertFalse(Path(result["ready_file"]).exists())
        registry = Path(result["registry_file"]).read_text()
        self.assertIn("startup dll", registry)
        self.assertNotIn("open_protk_unsigned_apps", registry)
        self.assertNotIn("open_protk_signed_apps", registry)
        boot = json.loads(
            (Path(result["module_file"]).parent / "callback_bootstrap.json").read_text()
        )
        self.assertEqual(boot["resource_root"], str(self.build.parent.resolve()))

    def test_repeat_prepare_preserves_loaded_binary_and_ready_state(self):
        first = prepare_callback(self.build, self.digest)
        dll = Path(first["module_file"])
        stamp = dll.stat().st_mtime_ns
        ready = Path(first["ready_file"])
        ready.write_text('{"operator_loaded":true}')
        self.assertEqual(prepare_callback(self.build, self.digest), first)
        self.assertEqual(dll.stat().st_mtime_ns, stamp)
        self.assertEqual(ready.read_text(), '{"operator_loaded":true}')

    def test_hash_mismatch_rejects_before_publishing_files(self):
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            prepare_callback(self.build, "0" * 64)
        self.assertFalse((self.build / "blend_callback_setup.json").exists())
        self.assertFalse((self.build / "blend_callback").exists())

    def test_tampered_immutable_copy_is_rejected_without_overwriting_it(self):
        result = prepare_callback(self.build, self.digest)
        copy = Path(result["module_file"])
        copy.write_bytes(b"unexpected content")
        with self.assertRaisesRegex(ValueError, "Immutable Blend callback"):
            prepare_callback(self.build, self.digest)
        self.assertEqual(copy.read_bytes(), b"unexpected content")

    def test_rebuild_publishes_new_version_without_changing_loaded_old_copy(self):
        old = prepare_callback(self.build, self.digest)
        self.dll.write_bytes(b"new callback")
        current_hash = hashlib.sha256(self.dll.read_bytes()).hexdigest()
        current = prepare_callback(self.build, current_hash)
        self.assertNotEqual(current["module_file"], old["module_file"])
        self.assertNotEqual(current["command"], old["command"])
        self.assertEqual(Path(old["module_file"]).read_bytes(), b"fixture callback")

    def test_distinct_deployments_do_not_register_the_same_command(self):
        first = prepare_callback(self.build, self.digest)
        other = self.build.parent / "second" / "build"
        other.mkdir(parents=True)
        (other / self.dll.name).write_bytes(self.dll.read_bytes())
        second = prepare_callback(other, self.digest)
        self.assertNotEqual(first["command"], second["command"])
        self.assertEqual(first["dll_sha256"], second["dll_sha256"])

    def test_public_status_does_not_expose_application_id_or_claim_runtime_ready(self):
        result = prepare_callback(self.build, self.digest)
        Path(result["ready_file"]).write_text('{"application_id":"private","initialize_code":0}')
        status = callback_setup_status(self.build)
        self.assertEqual(status["artifact_status"], "prepared")
        self.assertNotIn("private", json.dumps(status))
        self.assertNotIn("connected", status)
        self.assertNotIn("loaded", status)
        Path(result["module_file"]).write_bytes(b"tampered")
        self.assertEqual(callback_setup_status(self.build)["artifact_status"], "not_prepared")


if __name__ == "__main__":
    unittest.main()

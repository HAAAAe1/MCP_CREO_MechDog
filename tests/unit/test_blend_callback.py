"""Resident callback artifacts are immutable and never grant loader permission."""

import contextlib
import hashlib
import json
import subprocess
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch

import bridge
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
        (self.build / "creo_blend_loader.dll").write_bytes(b"fixture loader")
        self.prepare = partial(prepare_callback, loader_fingerprint="a" * 64)

    def test_verified_build_creates_setup_with_no_authorization_or_ready_claim(self):
        result = self.prepare(self.build, self.digest)
        self.assertEqual(Path(result["module_file"]).read_bytes(), self.dll.read_bytes())
        self.assertEqual(result["protocol"], 3)
        self.assertFalse(Path(result["ready_file"]).exists())
        registry = Path(result["registry_file"]).read_text()
        self.assertEqual(
            Path(result["registry_file"]), (self.build / "blend_callback_protk.dat").resolve()
        )
        self.assertEqual(result["registry_shortcut"], result["registry_file"])
        self.assertEqual(
            Path(result["persistent_registration_config"]).read_text(encoding="utf-8"),
            f"protkdat {result['registry_file']}\n",
        )
        self.assertIn("startup dll", registry)
        self.assertNotIn("open_protk_unsigned_apps", registry)
        self.assertNotIn("open_protk_signed_apps", registry)
        boot = json.loads(
            (Path(result["module_file"]).parent / "callback_bootstrap.json").read_text()
        )
        self.assertEqual(boot["resource_root"], str(self.build.parent.resolve()))

    def test_setup_instruction_leads_with_one_time_entry(self):
        # FEAT-029 guidance: the first sentence must be the actionable one-time
        # registration entry (registry file, DLL prompt, persistence, ready gate).
        result = self.prepare(self.build, self.digest)
        setup = result["setup"]
        self.assertTrue(
            setup.startswith("One-time setup: in Creo Auxiliary Applications register"),
            setup[:80],
        )
        self.assertIn("blend_callback_protk.dat", setup)
        self.assertIn("review the DLL prompt", setup)
        self.assertIn("never loaded automatically", setup)
        self.assertIn("only readiness=ready", setup)
        self.assertIn("need no callback", setup)
        self.assertIn("MCP never changes security policy", setup)

    def test_repeat_prepare_preserves_loaded_binary_and_ready_state(self):
        first = self.prepare(self.build, self.digest)
        dll = Path(first["module_file"])
        stamp = dll.stat().st_mtime_ns
        ready = Path(first["ready_file"])
        ready.write_text('{"operator_loaded":true}')
        self.assertEqual(self.prepare(self.build, self.digest), first)
        self.assertEqual(dll.stat().st_mtime_ns, stamp)
        self.assertEqual(ready.read_text(), '{"operator_loaded":true}')

    def test_hash_mismatch_rejects_before_publishing_files(self):
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            self.prepare(self.build, "0" * 64)
        self.assertFalse((self.build / "blend_callback_setup.json").exists())
        self.assertFalse((self.build / "blend_callback").exists())

    def test_tampered_immutable_copy_is_rejected_without_overwriting_it(self):
        result = self.prepare(self.build, self.digest)
        copy = Path(result["module_file"])
        copy.write_bytes(b"unexpected content")
        with self.assertRaisesRegex(ValueError, "Immutable Blend callback"):
            self.prepare(self.build, self.digest)
        self.assertEqual(copy.read_bytes(), b"unexpected content")

    def test_rebuild_publishes_new_version_without_changing_loaded_old_copy(self):
        old = self.prepare(self.build, self.digest)
        self.dll.write_bytes(b"new callback")
        current_hash = hashlib.sha256(self.dll.read_bytes()).hexdigest()
        current = self.prepare(self.build, current_hash)
        self.assertNotEqual(current["module_file"], old["module_file"])
        self.assertNotEqual(current["command"], old["command"])
        self.assertEqual(Path(old["module_file"]).read_bytes(), b"fixture callback")

    def test_distinct_deployments_do_not_register_the_same_command(self):
        first = self.prepare(self.build, self.digest)
        other = self.build.parent / "second" / "build"
        other.mkdir(parents=True)
        (other / self.dll.name).write_bytes(self.dll.read_bytes())
        (other / "creo_blend_loader.dll").write_bytes(b"fixture loader")
        second = self.prepare(other, self.digest)
        self.assertNotEqual(first["command"], second["command"])
        self.assertEqual(first["dll_sha256"], second["dll_sha256"])

    def test_payload_upgrade_and_rollback_preserve_registration_and_loaded_images(self):
        old = self.prepare(self.build, self.digest)
        registry = Path(old["registry_file"])
        original = registry.read_bytes()
        stamp = registry.stat().st_mtime_ns
        loader = Path(old["loader_file"])
        loader_stamp = loader.stat().st_mtime_ns
        self.dll.write_bytes(b"changed callback payload")
        newer = self.prepare(self.build, hashlib.sha256(self.dll.read_bytes()).hexdigest())
        self.assertEqual(newer["registry_file"], old["registry_file"])
        self.assertEqual(registry.read_bytes(), original)
        self.assertEqual(registry.stat().st_mtime_ns, stamp)
        self.assertEqual(loader.stat().st_mtime_ns, loader_stamp)
        self.assertEqual(Path(old["module_file"]).read_bytes(), b"fixture callback")
        pointer = loader.parent / "deployment.json"
        self.assertEqual(json.loads(pointer.read_text())["dll_sha256"], newer["dll_sha256"])
        self.dll.write_bytes(b"fixture callback")
        self.assertEqual(self.prepare(self.build, self.digest), old)
        self.assertEqual(json.loads(pointer.read_text())["dll_sha256"], self.digest)
        self.assertTrue(Path(newer["module_file"]).is_file())

    def test_loader_generation_change_keeps_public_entry_and_preserves_old_loader(self):
        old = self.prepare(self.build, self.digest)
        (self.build / "creo_blend_loader.dll").write_bytes(b"new incompatible loader")
        new = prepare_callback(self.build, self.digest, "b" * 64)
        self.assertEqual(old["registry_file"], new["registry_file"])
        self.assertNotEqual(old["registry_generation_file"], new["registry_generation_file"])
        self.assertEqual(Path(old["loader_file"]).read_bytes(), b"fixture loader")

    def test_failed_publication_keeps_previous_setup_and_no_partial_payload(self):
        old = self.prepare(self.build, self.digest)
        old_setup = (self.build / "blend_callback_setup.json").read_bytes()
        self.dll.write_bytes(b"candidate callback")
        digest = hashlib.sha256(self.dll.read_bytes()).hexdigest()
        with patch("creo_mechdog.blend_callback.os.link", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                self.prepare(self.build, digest)
        self.assertEqual((self.build / "blend_callback_setup.json").read_bytes(), old_setup)
        self.assertEqual(Path(old["module_file"]).read_bytes(), b"fixture callback")
        self.assertEqual(list((self.build / "blend_callback" / digest).iterdir()), [])

    def test_legacy_artifacts_never_claim_runtime_ready(self):
        (self.build / "blend_callback_setup.json").write_text('{"protocol":2}')
        value = callback_setup_status(self.build)
        self.assertEqual(value["artifact_status"], "legacy")
        self.assertEqual(value["readiness"], "unknown")

    def probe(self, result=None, exception=None):
        self.prepare(self.build, self.digest)
        (self.build / "creo_worker.exe").touch()
        with (
            patch.object(bridge, "ROOT", self.build.parent),
            patch.object(bridge, "toolkit_lock", return_value=contextlib.nullcontext()),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(bridge, "record_channel_health"),
            patch.object(bridge, "build_native") as build,
            patch.object(
                bridge.subprocess, "run", return_value=result, side_effect=exception
            ) as run,
        ):
            value = bridge.callback_status()
            build.assert_not_called()
            if run.called:
                self.assertEqual(run.call_args.kwargs["timeout"], 9)
            return value

    def test_live_result_is_required_even_when_old_ready_record_exists(self):
        result = self.prepare(self.build, self.digest)
        Path(result["ready_file"]).write_text('{"initialize_code":0,"protocol":3}')
        value = self.probe(subprocess.CompletedProcess([], 0, b'{"connected":true}'))
        self.assertEqual(value["readiness"], "unknown")
        self.assertEqual(value["reason"], "invalid_probe_result")

    def test_timeout_unreachable_and_bad_json_remain_unknown(self):
        values = [
            self.probe(exception=subprocess.TimeoutExpired("probe", 9)),
            self.probe(
                subprocess.CompletedProcess(
                    [], 20, b'{"connected":false,"connection_state":"no_session"}'
                )
            ),
            self.probe(subprocess.CompletedProcess([], 0, b"bad")),
        ]
        for value in values:
            self.assertEqual(value["readiness"], "unknown")
            self.assertEqual(value["registration_status"], "unknown")
        self.assertEqual(values[0]["reason"], "probe_timeout")

    def test_disconnect_failure_invalidates_a_successful_callback_response(self):
        value = self.probe(
            subprocess.CompletedProcess(
                [],
                0,
                json.dumps(
                    {
                        "connected": True,
                        "disconnect_code": -38,
                        "direct_blend_callback": {"readiness": "ready"},
                    }
                ).encode(),
            )
        )
        self.assertEqual(value["readiness"], "unknown")
        self.assertEqual(value["reason"], "disconnect_failed")

    def test_real_channel_contention_reports_unknown_and_preserves_the_holder(self):
        self.prepare(self.build, self.digest)
        (self.build / "creo_worker.exe").touch()
        with (
            patch.object(bridge, "ROOT", self.build.parent),
            bridge.toolkit_lock(operation="execute_plan", job_id="a" * 32),
            patch.object(bridge.subprocess, "run") as run,
        ):
            value = bridge.callback_status()
        self.assertEqual(value["readiness"], "unknown")
        self.assertEqual(value["reason"], "channel_busy")
        self.assertEqual(value["session"]["blocking_job_id"], "a" * 32)
        run.assert_not_called()

    def test_live_ready_is_timestamped_but_registration_remains_unknown(self):
        value = self.probe(
            subprocess.CompletedProcess(
                [],
                0,
                json.dumps(
                    {
                        "connected": True,
                        "disconnect_code": 0,
                        "direct_blend_callback": {
                            "readiness": "ready",
                            "reason": "live_identity_verified",
                        },
                    }
                ).encode(),
            )
        )
        self.assertEqual(value["readiness"], "ready")
        self.assertTrue(value["snapshot"])
        self.assertIn("checked_at", value)
        self.assertEqual(value["registration_status"], "unknown")

    def test_public_status_does_not_expose_application_id_or_claim_runtime_ready(self):
        result = self.prepare(self.build, self.digest)
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

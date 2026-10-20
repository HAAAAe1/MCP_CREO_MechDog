"""creo_open_file contracts; native workers are substituted, never connect Creo."""

import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog import open_file as opener
from tests.unit import test_adoption as fixture


def _touch(path: Path, content: bytes = b"native model bytes") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class SelectFileRules(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="open_file_select_")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()

    def test_explicit_version_opens_exactly_that_file(self):
        first = _touch(self.directory / "part 零件 v1.prt.1", b"one")
        second = _touch(self.directory / "part 零件 v1.prt.2", b"two")
        selected, kind, version = opener.select_file(str(second))
        self.assertEqual(selected, second)
        self.assertEqual((kind, version), ("part", 2))
        self.assertNotEqual(selected, first)

    def test_omitted_version_selects_highest_numeric(self):
        _touch(self.directory / "model.prt.1", b"one")
        _touch(self.directory / "model.prt.7", b"seven")
        _touch(self.directory / "model.prt.3", b"three")
        selected, kind, version = opener.select_file(str(self.directory / "model.prt"))
        self.assertEqual(selected.name, "model.prt.7")
        self.assertEqual((kind, version), ("part", None))

    def test_plain_file_only_when_no_numeric_version_exists(self):
        plain = _touch(self.directory / "model with spaces.asm", b"assembly")
        selected, kind, version = opener.select_file(str(plain))
        self.assertEqual(selected, plain)
        self.assertEqual((kind, version), ("assembly", None))

    def test_numeric_version_beats_plain_file(self):
        _touch(self.directory / "model.prt", b"plain")
        _touch(self.directory / "model.prt.2", b"two")
        selected, _, _ = opener.select_file(str(self.directory / "model.prt"))
        self.assertEqual(selected.name, "model.prt.2")

    def test_case_insensitive_lookup_but_ambiguous_spellings_rejected(self):
        stored = _touch(self.directory / "MODEL.PRT.4")
        selected, _, _ = opener.select_file(str(self.directory / "model.prt.4"))
        self.assertEqual(selected, stored)
        with patch.object(opener.os, "listdir", return_value=["MODEL.PRT.5", "model.prt.5"]):
            with self.assertRaisesRegex(ValueError, "Ambiguous"):
                opener.select_file(str(self.directory / "model.prt.5"))

    def test_rejects_relative_unknown_and_malformed_paths(self):
        _touch(self.directory / "real.prt.1")
        for bad, message in (
            ("real.prt", "absolute"),
            (str(self.directory / "missing.prt.1"), "not found"),
            (str(self.directory / "missing.prt"), "not found"),
            (str(self.directory / "notes.txt"), "must end with"),
            (str(self.directory / "model.prt.0"), "start at 1"),
            (str(self.directory / "model.prt.abc"), "must end with"),
            (str(self.directory / "no_directory_here/real.prt"), "Directory does not exist"),
        ):
            with self.assertRaisesRegex(ValueError, message):
                opener.select_file(bad)


class OpenFileSubmission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="open_file_submit_")
        self.addCleanup(temporary.cleanup)
        self.directory = fixture.prepare_root(Path(temporary.name))
        self.source = _touch(self.directory / "user_parts" / "外部 part.prt.2")
        stack = ExitStack()
        self.addCleanup(stack.close)
        for obj, name, value in (
            (bridge, "ROOT", self.directory),
            (bridge, "JOBS", self.directory / "jobs"),
        ):
            stack.enter_context(patch.object(obj, name, value))
        stack.enter_context(patch.object(opener.subprocess, "Popen", return_value=None))

    def test_submit_returns_queued_job_and_persists_intent(self):
        manifest = opener.open_file(str(self.source), "open-key-0001")
        self.assertEqual(manifest["kind"], "open_file")
        self.assertEqual(manifest["status"], "queued")
        self.assertIsNone(manifest["model_id"])
        request = bridge.read_json(bridge.job_path(manifest["job_id"]) / "request.json")
        self.assertEqual(request["open_file"]["model_kind"], "part")
        self.assertEqual(request["open_file"]["explicit_version"], 2)
        self.assertTrue(request["readonly"])
        self.assertIn("identity_before", request["open_file"])

    def test_same_key_replays_and_changed_path_rejects(self):
        first = opener.open_file(str(self.source), "open-key-0002")
        with patch.object(
            bridge, "get_job", return_value={"job_id": first["job_id"], "status": "succeeded"}
        ) as replay:
            second = opener.open_file(str(self.source), "open-key-0002")
        self.assertEqual(second["job_id"], first["job_id"])
        self.assertEqual(replay.call_count, 1)
        other = _touch(self.directory / "user_parts" / "另一个.prt.1")
        with self.assertRaisesRegex(ValueError, "another open-file request"):
            opener.open_file(str(other), "open-key-0002")

    def test_bad_keys_and_paths_rejected_before_any_job(self):
        for key in ("short", "has space", "x" * 81, ""):
            with self.assertRaises(ValueError):
                opener.open_file(str(self.source), key)
        with self.assertRaises(ValueError):
            opener.open_file("relative.prt", "open-key-0003")
        self.assertEqual(list((self.directory / "jobs").iterdir()), [])


def _native_result(directory: Path, payload: dict) -> None:
    fixture._write(directory / "native_result.json", payload)


class OpenFileRun(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="open_file_run_")
        self.addCleanup(temporary.cleanup)
        self.directory = fixture.prepare_root(Path(temporary.name))
        self.source = _touch(self.directory / "user_parts" / "run part.prt.1")
        stack = ExitStack()
        self.addCleanup(stack.close)
        for obj, name, value in (
            (bridge, "ROOT", self.directory),
            (bridge, "JOBS", self.directory / "jobs"),
        ):
            stack.enter_context(patch.object(obj, name, value))
        stack.enter_context(patch.object(opener.subprocess, "Popen", return_value=None))
        stack.enter_context(patch.object(opener.bridge, "build_native", return_value=Path("w")))
        self.manifest = opener.open_file(str(self.source), "open-key-run-1")
        self.job = bridge.job_path(self.manifest["job_id"])

    def _run(self, result: dict | None, returncode: int = 0) -> dict:
        if result is not None:
            _native_result(self.job, result)

        def fake_run(*args, **kwargs):
            if returncode:
                raise subprocess.CalledProcessError(returncode, args[0])
            return subprocess.CompletedProcess(args[0], 0)

        with patch.object(opener.subprocess, "run", side_effect=fake_run):
            opener.run(self.manifest["job_id"], dict(self.manifest))
        return bridge.read_json(self.job / "job.json")

    def test_success_records_identity_and_no_managed_model(self):
        finished = self._run(
            {
                "success": True,
                "delivery_complete": True,
                "disconnect_code": 0,
                "open_file": {"selected_file": str(self.source), "displayed": True},
                "session_fingerprint": "fingerprint-fixture",
            }
        )
        self.assertEqual(finished["status"], "succeeded")
        report = finished["result"]
        self.assertIsNone(report["model_id"])
        self.assertFalse(report["adopted"])
        after = report["open_file"]["identity_after"]
        self.assertEqual(after["sha256"], report["open_file"]["identity_before"]["sha256"])
        self.assertFalse(report["open_file"]["source_file_changed_during_open"])

    def test_incomplete_delivery_is_unknown_outcome(self):
        finished = self._run({"success": True, "delivery_complete": False, "disconnect_code": 0})
        self.assertEqual(finished["status"], "unknown_outcome")
        self.assertTrue(finished["recovery_required"])

    def test_native_failure_is_failed_with_message(self):
        finished = self._run(
            {
                "success": False,
                "delivery_complete": True,
                "disconnect_code": 0,
                "message": "SESSION_NAME_CONFLICT: fixture",
                "open_file": {"loaded": False},
            }
        )
        self.assertEqual(finished["status"], "failed")
        self.assertIn("SESSION_NAME_CONFLICT", finished["message"])

    def test_source_change_during_open_is_reported_not_hidden(self):
        with patch.object(
            opener,
            "_identity",
            side_effect=lambda path: {"sha256": "changed", "path": str(path)},
        ):
            finished = self._run(
                {
                    "success": True,
                    "delivery_complete": True,
                    "disconnect_code": 0,
                    "open_file": {"selected_file": str(self.source), "displayed": True},
                }
            )
        self.assertEqual(finished["status"], "succeeded")
        self.assertTrue(finished["result"]["open_file"]["source_file_changed_during_open"])


if __name__ == "__main__":
    unittest.main()

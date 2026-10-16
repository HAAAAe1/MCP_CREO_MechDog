"""BUG-009: real process exclusion, actionable rejection and finalization order."""

import asyncio
import errno
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
import server


class ToolkitChannel(unittest.TestCase):
    def setUp(self):
        self.checkout = bridge.ROOT
        parent = self.checkout / ".tmp"
        parent.mkdir(exist_ok=True)
        directory = self.enterContext(tempfile.TemporaryDirectory(dir=parent, prefix="bug009_"))
        self.root = Path(directory)
        self.enterContext(patch.object(bridge, "ROOT", self.root))
        self.enterContext(patch.object(bridge, "JOBS", self.root / "jobs"))
        self.enterContext(patch.object(general, "MODELS", self.root / "models"))
        self.enterContext(
            patch.object(bridge, "config", return_value={"creo_root": str(self.root)})
        )
        template = self.root / "Common Files/templates/mmns_part_solid_abs.prt"
        template.parent.mkdir(parents=True)
        template.write_bytes(b"not a native template")

    def child(self, code):
        result = subprocess.run(
            [sys.executable, "-c", code, str(self.root)],
            cwd=self.checkout,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=bridge.HIDDEN,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def contender(self):
        return self.child("""
import bridge,json,sys
from pathlib import Path
bridge.ROOT=Path(sys.argv[1])
try:
    with bridge.toolkit_lock():
        print(json.dumps({'acquired':True}))
except bridge.ToolkitBusy as exc:
    print(json.dumps(exc.payload))
""")

    def submit(self, **kwargs):
        with patch.object(bridge.subprocess, "Popen"):
            return general.submit([], **kwargs)

    def worker(self, created, outcome="success"):
        def run(*args, **kwargs):
            if outcome == "timeout":
                raise subprocess.TimeoutExpired(args[0], 1)
            part = general.model_path(created["model_id"]) / "output/fixture.prt.1"
            part.write_bytes(b"synthetic native result")
            bridge.write_json(
                bridge.job_path(created["job_id"]) / "native_result.json",
                {
                    "success": outcome == "success",
                    "part_file": str(part),
                    "saved_file_reloaded_and_verified": True,
                    "inspection": {"volume_mm3": 10},
                    "aliases": {},
                    "rollback_succeeded": outcome == "failure",
                    "message": "controlled outcome",
                },
            )
            return subprocess.CompletedProcess(args[0], 0 if outcome == "success" else 1)

        return run

    def run_job(self, created, outcome="success"):
        with (
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe"),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(bridge.subprocess, "run", side_effect=self.worker(created, outcome)),
        ):
            bridge.run_job(created["job_id"])

    def test_cross_process_busy_identifies_holder_and_release_allows_retry(self):
        with bridge.toolkit_lock(operation="execute_plan", job_id="a" * 32, model_id="b" * 32):
            busy = self.contender()
            self.assertEqual(busy["blocking_job_id"], "a" * 32)
            self.assertEqual(busy["blocking_model_id"], "b" * 32)
            self.assertEqual(busy["blocking_operation"], "execute_plan")
            self.assertFalse(busy["accepted"])
            self.assertEqual(busy["retry_after_seconds"], 1)
            self.assertIn("unknown_outcome", busy["retry_guidance"])
        self.assertEqual(self.contender(), {"acquired": True})
        self.assertFalse((self.root / "toolkit-owner.lock").exists())

    def test_unknown_owner_and_non_job_owner_do_not_invent_job(self):
        with bridge.toolkit_lock(operation="session_status"):
            self.assertIsNone(self.contender()["blocking_job_id"])
            (self.root / "toolkit-owner.lock").write_text("partial", encoding="utf-8")
            unknown = self.contender()
            self.assertFalse(unknown["owner_determined"])
            self.assertIsNone(unknown["blocking_job_id"])
            self.assertIn("No occupying job", unknown["retry_guidance"])

    def test_owner_publish_failure_releases_os_lock(self):
        with patch.object(bridge, "write_json", side_effect=OSError("metadata unavailable")):
            with self.assertRaises(OSError), bridge.toolkit_lock():
                self.fail("Admission must fail before native work")
        self.assertEqual(self.contender(), {"acquired": True})

    def test_non_contention_lock_error_is_not_mislabeled_busy(self):
        with patch.object(bridge.msvcrt, "locking", side_effect=OSError(errno.EIO, "I/O failure")):
            with self.assertRaises(OSError) as error, bridge.toolkit_lock():
                self.fail("Unexpected acquisition")
        self.assertNotIsInstance(error.exception, bridge.ToolkitBusy)

    def test_real_stdio_preserves_busy_fields_and_polling_during_contention(self):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters

        bridge.JOBS.mkdir()
        job_id = "a" * 32
        directory = bridge.JOBS / job_id
        directory.mkdir()
        bridge.write_json(
            directory / "job.json",
            {
                "job_id": job_id,
                "status": "running",
                "created_at": bridge.now(),
                "kind": "generic",
            },
        )
        bootstrap = """
import bridge,generic_bridge,server,sys
from pathlib import Path
bridge.ROOT=Path(sys.argv[1])
bridge.JOBS=bridge.ROOT/'jobs'
generic_bridge.MODELS=bridge.ROOT/'models'
bridge.config=lambda:{'generic_timeout_seconds':600}
server.startup.start=lambda:None
server.startup.require_ready=lambda:None
server.updates.start=lambda:None
server.mcp.run()
"""

        async def check():
            async with Client(
                StdioServerParameters(
                    command=sys.executable,
                    args=["-c", bootstrap, str(self.root)],
                    cwd=self.checkout,
                ),
                read_timeout_seconds=10,
            ) as client:
                busy, poll, models = await asyncio.gather(
                    client.call_tool("creo_refresh_model", {"model_id": "b" * 32}),
                    client.call_tool("creo_get_job", {"job_id": job_id, "detail": "compact"}),
                    client.call_tool("creo_list_models", {}),
                )
                self.assertTrue(busy.is_error)
                self.assertFalse(busy.structured_content["accepted"])
                self.assertEqual(busy.structured_content["blocking_job_id"], job_id)
                self.assertEqual(json.loads(busy.content[0].text), busy.structured_content)
                self.assertFalse(poll.is_error)
                self.assertEqual(poll.structured_content["status"], "running")
                self.assertFalse(models.is_error)

        with bridge.toolkit_lock(operation="execute_plan", job_id=job_id, model_id="b" * 32):
            asyncio.run(check())

    def test_pending_job_rejects_before_worker_acquires_channel(self):
        first = self.submit()
        with self.assertRaises(bridge.ToolkitBusy) as error:
            self.submit(model_id=first["model_id"], expected_revision=0)
        self.assertEqual(error.exception.payload["blocking_job_id"], first["job_id"])
        self.assertEqual(error.exception.payload["blocking_operation"], "pending_job")
        self.assertEqual(len(list(bridge.JOBS.iterdir())), 1)

    def test_model_finalizes_under_lock_and_terminal_publishes_after_unlock(self):
        first = self.submit()
        real_write = bridge.write_json
        observed = []

        def write(path, value):
            if path.name == "model.json" and value.get("pending_job") is None:
                # Separate interpreter, so the test does not confuse a thread mutex with OS exclusion.
                observed.append(("model", self.contender()))
            if path.name == "job.json" and value["status"] == "succeeded":
                observed.append(("terminal", self.contender()))
            real_write(path, value)

        # The contender itself uses subprocess.run; keep the native stub specific to worker calls.
        native = self.worker(first)
        real_run = subprocess.run

        def run(args, **kwargs):
            return real_run(args, **kwargs) if "-c" in args else native(args, **kwargs)

        with (
            patch.object(bridge, "write_json", side_effect=write),
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe"),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(bridge.subprocess, "run", side_effect=run),
        ):
            bridge.run_job(first["job_id"])
        self.assertEqual(observed[0][1]["blocking_job_id"], first["job_id"])
        self.assertEqual(observed[1], ("terminal", {"acquired": True}))
        job = bridge.get_job(first["job_id"])
        self.assertEqual(job["status"], "succeeded")
        second = self.submit(model_id=first["model_id"], expected_revision=job["revision"])
        self.assertEqual(general.model_info(first["model_id"])["pending_job"], second["job_id"])

    def test_succeeded_job_does_not_reserve_channel_against_another_owner(self):
        first = self.submit()
        self.run_job(first)
        with bridge.toolkit_lock(operation="session_status"):
            self.assertEqual(bridge.get_job(first["job_id"])["status"], "succeeded")
            general.list_models()
            general.inspect_model(first["model_id"])
            with self.assertRaises(bridge.ToolkitBusy) as error:
                self.submit(model_id=first["model_id"], expected_revision=1)
            self.assertEqual(error.exception.payload["blocking_operation"], "session_status")
            self.assertIsNone(error.exception.payload["blocking_job_id"])

    def test_rollback_and_timeout_keep_revision_and_readiness_guards(self):
        first = self.submit()
        self.run_job(first)
        mid = first["model_id"]
        for outcome, status in (("failure", "failed"), ("timeout", "unknown_outcome")):
            task = self.submit(model_id=mid, expected_revision=1)
            self.run_job(task, outcome)
            self.assertEqual(bridge.get_job(task["job_id"])["status"], status)
            model = general.model_info(mid)
            self.assertEqual(model["revision"], 1)
            self.assertEqual(model["pending_job"], task["job_id"] if outcome == "timeout" else None)
        with self.assertRaises(bridge.ToolkitBusy):
            self.submit(model_id=mid, expected_revision=1)

    def test_channel_wait_timeout_does_not_overwrite_reserved_model(self):
        task = self.submit()
        before = general.model_info(task["model_id"])
        with patch.object(bridge, "toolkit_lock", side_effect=bridge.ToolkitBusy()):
            bridge.run_job(task["job_id"])
        self.assertEqual(general.model_info(task["model_id"]), before)
        terminal = bridge.get_job(task["job_id"])
        self.assertEqual(terminal["status"], "failed")
        self.assertIn("retained", terminal["recovery_required"])

    def test_mcp_busy_is_structured_error_and_other_errors_stay_errors(self):
        task = self.submit()
        with (
            bridge.toolkit_lock(
                operation="execute_plan", job_id=task["job_id"], model_id=task["model_id"]
            ),
            patch.object(server.startup, "require_ready"),
        ):
            result = asyncio.run(server.creo_refresh_model(task["model_id"]))
        self.assertTrue(result.is_error)
        self.assertEqual(result.structured_content["blocking_job_id"], task["job_id"])
        self.assertEqual(json.loads(result.content[0].text), result.structured_content)
        self.assertFalse(result.structured_content["accepted"])


if __name__ == "__main__":
    unittest.main()

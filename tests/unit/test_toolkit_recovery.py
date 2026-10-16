"""BUG-008: bounded recovery and unknown outcomes must preserve write protection."""

import contextlib
import subprocess
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import bridge
import creo_startup
import generic_bridge as general
from creo_mechdog.recovery import process_identity
from tests.unit import test_toolkit_channel as channel_tests


class ToolkitRecovery(unittest.TestCase):
    setUp = channel_tests.ToolkitChannel.setUp
    submit = channel_tests.ToolkitChannel.submit
    worker = channel_tests.ToolkitChannel.worker
    run_job = channel_tests.ToolkitChannel.run_job

    def test_probe_timeout_is_actionable_and_invalidates_old_ready(self):
        startup = creo_startup.CreoStartup()
        startup._publish("ready", "fixture", shared=False, verified_at=bridge.now())
        with (
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe"),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(
                bridge.subprocess, "run", side_effect=subprocess.TimeoutExpired("probe", 9)
            ),
        ):
            value = bridge.session_status(2)
        self.assertEqual(value["connection_state"], "probe_timeout")
        self.assertEqual(value["probe_budget_seconds"], 9)
        self.assertIn("preserve unknown", value["message"])
        self.assertFalse(startup.status()["connected"])
        self.assertEqual(startup.status()["state"], "timeout")

    def test_public_probe_does_not_rebuild_and_invalid_json_is_not_ready(self):
        (self.root / "build").mkdir()
        (self.root / "build/creo_worker.exe").write_bytes(b"fixture")
        with (
            patch.object(bridge, "build_native") as build,
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(
                bridge.subprocess, "run", return_value=subprocess.CompletedProcess([], 31, b"bad")
            ),
        ):
            value = bridge.session_status(2, build_worker=False)
        self.assertEqual(value["connection_state"], "invalid_probe_result")
        self.assertFalse(value["connected"])
        build.assert_not_called()

    def test_disconnect_failure_never_commits_revision(self):
        created = self.submit()
        worker = self.worker(created)

        def failed_disconnect(*args, **kwargs):
            value = worker(*args, **kwargs)
            file = bridge.job_path(created["job_id"]) / "native_result.json"
            result = bridge.read_json(file)
            result.update(disconnect_code=-38, delivery_complete=True)
            bridge.write_json(file, result)
            return value

        with (
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe"),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(bridge.subprocess, "run", side_effect=failed_disconnect),
        ):
            bridge.run_job(created["job_id"])
        model = general.model_info(created["model_id"])
        self.assertEqual(model["revision"], 0)
        self.assertEqual(model["pending_job"], created["job_id"])
        self.assertEqual(bridge.get_job(created["job_id"])["status"], "unknown_outcome")

    def test_pre_disconnect_checkpoint_is_evidence_and_pending_survives_timeout(self):
        created = self.submit()
        directory = bridge.job_path(created["job_id"])
        checkpoint = {
            "success": True,
            "delivery_complete": False,
            "completion_stage": "before_disconnect",
            "saved_file_reloaded_and_verified": True,
        }
        bridge.write_json(directory / "native_checkpoint.json", checkpoint)
        self.run_job(created, "timeout")
        job = bridge.get_job(created["job_id"], detail="compact")
        self.assertEqual(job["status"], "unknown_outcome")
        evidence = job["recovery"]["native_checkpoint"]
        self.assertTrue(evidence["success"])
        self.assertFalse(evidence["authoritative_job_success"])
        self.assertEqual(general.model_info(created["model_id"])["revision"], 0)
        self.assertEqual(general.model_info(created["model_id"])["pending_job"], created["job_id"])
        before = (directory / "job.json").read_bytes()
        bridge.get_job(created["job_id"])
        self.assertEqual((directory / "job.json").read_bytes(), before)
        with self.assertRaises(bridge.ToolkitBusy):
            self.submit(model_id=created["model_id"], expected_revision=0)

    def test_build_timeout_does_not_claim_native_worker_ran(self):
        created = self.submit()
        with patch.object(
            bridge, "build_native", side_effect=subprocess.TimeoutExpired("build", 120)
        ):
            bridge.run_job(created["job_id"])
        self.assertEqual(bridge.get_job(created["job_id"])["status"], "failed")
        self.assertIsNone(general.model_info(created["model_id"])["pending_job"])
        self.assertIn("No native", bridge.get_job(created["job_id"])["message"])

    def test_runner_identity_distinguishes_process_instances(self):
        identity = process_identity(bridge.os.getpid())
        self.assertTrue(identity["alive"])
        self.assertGreater(identity["created"], 0)

    def test_readiness_snapshot_has_age_and_stale_marker(self):
        startup = creo_startup.CreoStartup()
        old = (datetime.now(timezone.utc) - timedelta(seconds=31)).isoformat()
        startup._publish("ready", "fixture", shared=False, verified_at=old)
        state = startup.status()
        self.assertTrue(state["snapshot"])
        self.assertTrue(state["stale"])
        self.assertGreaterEqual(state["verification_age_seconds"], 31)


class StartupRecovery(unittest.TestCase):
    def test_completed_attempt_deadline_does_not_poison_a_later_live_probe(self):
        from tests.test_creo_startup import CreoStartupTests

        fixture = CreoStartupTests()
        fixture.setUp()
        try:

            def drive(*args):
                fixture.startup._phase_deadline = fixture.clock.elapsed + 1
                fixture.startup._publish(
                    "ready", "fixture verified", shared=False, verified_at=bridge.now()
                )

            with patch.object(fixture.startup, "_drive", side_effect=drive):
                fixture.startup._run(False)
            self.assertIsNone(fixture.startup._attempt_deadline)
            self.assertIsNone(fixture.startup._phase_deadline)
            fixture.clock.elapsed += 2
            self.assertTrue(fixture.startup.session_status()["startup"]["connected"])
        finally:
            fixture.doCleanups()

    def test_waiter_does_not_publish_pre_retry_ready_while_leader_rechecks(self):
        from tests.test_creo_startup import CreoStartupTests

        fixture = CreoStartupTests()
        fixture.setUp()
        try:
            bridge.write_json(
                fixture.coordinator / "state.json",
                {
                    "state": "ready",
                    "connected": True,
                    "launch_attempt": 0,
                    "launch_reserved": False,
                    "updated_at": (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat(),
                },
            )
            observed = []
            original_wait = fixture.clock.wait

            def wait(seconds):
                observed.append(fixture.startup.status())
                original_wait(seconds)

            with (
                patch.object(
                    creo_startup,
                    "coordination_lock",
                    side_effect=[creo_startup.CoordinatorBusy(), contextlib.nullcontext()],
                ),
                patch.object(fixture.clock, "wait", side_effect=wait),
                patch.object(fixture.startup, "_drive") as drive,
            ):
                fixture.startup._run(True)
            self.assertEqual(len(observed), 1)
            self.assertFalse(observed[0]["connected"])
            self.assertEqual(observed[0]["state"], "checking")
            drive.assert_called_once()
        finally:
            fixture.doCleanups()

    def test_hung_builder_reports_deadline_and_retry_reuses_in_flight_thread(self):
        startup = creo_startup.CreoStartup()
        entered, release = threading.Event(), threading.Event()

        def hung(*args):
            startup._attempt_deadline = time.monotonic() + 10
            startup._phase_deadline = time.monotonic() + 0.1
            startup._publish("building_worker", "controlled blocked build", shared=False)
            entered.set()
            release.wait(5)
            startup._publish("ready", "late result must not override timeout", shared=False)

        with patch.object(startup, "_run", side_effect=hung):
            startup.start()
            self.assertTrue(entered.wait(2))
            thread = startup._thread
            time.sleep(0.15)
            began = time.monotonic()
            state = startup.status()
            self.assertLess(time.monotonic() - began, 0.5)
            self.assertEqual(state["state"], "timeout")
            self.assertFalse(state["connected"])
            self.assertTrue(state["coordinator_running"])
            startup.start(retry=True)
            self.assertIs(startup._thread, thread)
            release.set()
            thread.join(2)
            self.assertEqual(startup.status()["state"], "timeout")

    def test_total_deadline_includes_channel_wait_and_does_not_reset(self):
        # Use the existing deterministic startup fixture without collecting its tests twice.
        from tests.test_creo_startup import CreoStartupTests

        fixture = CreoStartupTests()
        fixture.setUp()
        try:
            fixture.inventory.return_value = fixture.existing()
            fixture.probe.return_value = {
                "connected": False,
                "connection_state": "connection_failed",
                "toolkit_code": -38,
            }
            attempts = 0

            def lock(**kwargs):
                nonlocal attempts
                attempts += 1
                if attempts < 7:
                    raise bridge.ToolkitBusy(holder={"job_id": "a" * 32})
                return contextlib.nullcontext()

            with patch.object(bridge, "toolkit_lock", side_effect=lock):
                fixture.startup._drive(creo_startup.Settings.load(), True, 5)
            self.assertEqual(fixture.clock.elapsed, 5)
            self.assertEqual(fixture.startup.status()["state"], "timeout")
            fixture.launch.assert_not_called()
            trace = (fixture.coordinator / "startup.log").read_text(encoding="utf-8")
            self.assertIn("waiting_for_channel", trace)
            self.assertIn("building_worker", trace)
        finally:
            fixture.doCleanups()

    def test_probe_busy_is_prompt_and_does_not_claim_live_connection(self):
        startup = creo_startup.CreoStartup()
        startup._publish("ready", "fixture", shared=False, verified_at=bridge.now())
        with patch.object(
            bridge, "session_status", side_effect=bridge.ToolkitBusy(holder={"job_id": "a" * 32})
        ):
            state = startup.session_status()
        self.assertFalse(state["connected"])
        self.assertEqual(state["connection_state"], "busy")
        self.assertEqual(state["blocking_job_id"], "a" * 32)


if __name__ == "__main__":
    unittest.main()

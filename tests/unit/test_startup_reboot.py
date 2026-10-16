"""Reboot reconciliation must not release an unknown modeling operation."""

import contextlib
import hashlib
import json
import subprocess
import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import bridge
import creo_startup
from creo_mechdog import windows_boot
from creo_mechdog.startup_state import StartupStateError, archive_preboot_state
from tests import test_creo_startup as startup_tests


class StartupReboot(unittest.TestCase):
    def setUp(self):
        self.fixture = startup_tests.CreoStartupTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.path = self.fixture.coordinator / "state.json"
        self.raw = b"\0" * 380
        self.path.write_bytes(self.raw)
        # Simulate a later reboot; the provider itself is tested independently.
        started = datetime.now(timezone.utc) + timedelta(seconds=30)
        self.boot = {
            "time_ns": int(started.timestamp() * 1e9),
            "started_at": started.isoformat(),
            "source": "controlled reboot evidence",
        }
        self.boot_query = self.enterContext(
            patch.object(creo_startup, "boot_info", return_value=self.boot)
        )

    def controller(self):
        return creo_startup.CreoStartup(self.fixture.coordinator)

    def finish(self, controller):
        controller._thread.join(3)
        self.assertFalse(controller._thread.is_alive())
        return controller.status()

    def test_previous_boot_archive_is_durable_before_one_launch(self):
        launched = threading.Event()

        def launch(*args):
            state = bridge.read_json(self.path)
            self.assertTrue(state["launch_reserved"])
            self.assertEqual(state["launch_attempt"], 1)
            archive = self.fixture.coordinator / "history"
            self.assertEqual([p.read_bytes() for p in archive.iterdir()], [self.raw])
            launched.set()
            return self.fixture.process

        self.fixture.launch.side_effect = launch
        self.fixture.inventory.side_effect = lambda settings: (
            self.fixture.existing() if launched.is_set() else {"processes": [], "uncertain": False}
        )
        controller = self.controller()
        controller.start(retry=True)
        state = self.finish(controller)
        self.assertEqual(state["state"], "ready")
        self.assertTrue(state["launched_by_coordinator"])
        self.assertTrue(state["launch_state_known"])
        self.assertFalse(state["launch_reserved"])
        self.assertEqual(
            state["startup_recovery"]["original_sha256"], hashlib.sha256(self.raw).hexdigest()
        )
        self.assertTrue(state["startup_recovery"]["job_model_reservations_preserved"])
        self.fixture.launch.assert_called_once()

    def test_two_controllers_share_one_recovery_archive_and_launch(self):
        entered, release = threading.Event(), threading.Event()

        def launch(*args):
            entered.set()
            self.assertTrue(release.wait(2))
            return self.fixture.process

        self.fixture.launch.side_effect = launch
        self.fixture.inventory.side_effect = lambda settings: (
            self.fixture.existing() if release.is_set() else {"processes": [], "uncertain": False}
        )
        first, second = self.controller(), self.controller()
        first.start(retry=True)
        try:
            self.assertTrue(entered.wait(2))
            second.start(retry=True)
        finally:
            release.set()
        for controller in (first, second):
            self.assertEqual(self.finish(controller)["state"], "ready")
        self.assertEqual(len(list((self.fixture.coordinator / "history").iterdir())), 1)
        self.fixture.launch.assert_called_once()

    def test_same_boot_damage_cannot_authorize_replacement(self):
        self.boot["time_ns"] -= 3600 * 1_000_000_000
        controller = self.controller()
        controller.start(retry=True)
        state = self.finish(controller)
        self.assertEqual(state["state"], "selection_required")
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertIn("predate", state["coordination_error"]["automatic_recovery"]["reason"])
        self.fixture.launch.assert_not_called()

    def test_unverified_boot_keeps_damage_and_reservation_unknown(self):
        self.boot_query.return_value = None
        controller = self.controller()
        controller.start(retry=True)
        state = self.finish(controller)
        self.assertEqual(state["state"], "selection_required")
        self.assertFalse(state["launch_state_known"])
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.fixture.launch.assert_not_called()

    def test_backup_failure_never_replaces_state_or_launches(self):
        with patch.object(creo_startup, "archive_preboot_state", side_effect=OSError("denied")):
            controller = self.controller()
            controller.start(retry=True)
            self.assertEqual(self.finish(controller)["state"], "selection_required")
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.fixture.launch.assert_not_called()

    def test_replacement_failure_keeps_original_and_archive_without_launching(self):
        with patch.object(bridge, "write_json", side_effect=OSError("replace denied")):
            controller = self.controller()
            controller.start(retry=True)
            state = self.finish(controller)
        self.assertEqual(state["state"], "selection_required")
        self.assertFalse(state["automatic_launch_allowed"])
        self.assertEqual(state["startup_recovery"]["status"], "archived_replacement_failed")
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertEqual(
            [p.read_bytes() for p in (self.fixture.coordinator / "history").iterdir()], [self.raw]
        )
        self.fixture.launch.assert_not_called()

    def test_existing_or_uncertain_session_never_resets_startup_history(self):
        for current in (self.fixture.existing(), {"processes": [], "uncertain": True}):
            with self.subTest(current=current):
                self.fixture.inventory.return_value = current
                controller = self.controller()
                controller.start(retry=True)
                self.finish(controller)
                self.assertEqual(self.path.read_bytes(), self.raw)
        self.boot_query.assert_not_called()
        self.fixture.launch.assert_not_called()

    def test_session_appearing_while_acquiring_locks_prevents_reset(self):
        self.fixture.inventory.side_effect = [
            {"processes": [], "uncertain": False},
            self.fixture.existing(),
        ]
        controller = self.fixture.startup
        result = controller._restore_preboot_history(
            creo_startup.Settings.load(), StartupStateError("fixture"), 10
        )
        self.assertFalse(result)
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.fixture.launch.assert_not_called()

    def test_toolkit_busy_wait_is_bounded_without_backup_or_launch(self):
        controller = self.fixture.startup
        with patch.object(bridge, "toolkit_lock", side_effect=bridge.ToolkitBusy()):
            self.assertFalse(
                controller._restore_preboot_history(
                    creo_startup.Settings.load(), StartupStateError("fixture"), 1
                )
            )
        self.assertEqual(self.fixture.clock.elapsed, 1)
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.fixture.launch.assert_not_called()

    def test_boot_query_and_build_share_one_preparation_budget(self):
        def boot():
            self.fixture.clock.elapsed += 4
            return self.boot

        self.boot_query.side_effect = boot
        controller = self.fixture.startup
        self.assertTrue(
            controller._restore_preboot_history(
                creo_startup.Settings.load(), StartupStateError("fixture"), 310
            )
        )
        self.fixture.build.side_effect = lambda: setattr(
            self.fixture.clock, "elapsed", self.fixture.clock.elapsed + 177
        )
        controller._drive(creo_startup.Settings.load(), True, 310)
        self.assertEqual(controller.status()["state"], "timeout")
        self.fixture.launch.assert_not_called()

    def test_disabled_startup_and_selected_session_are_not_reset(self):
        for values in ({"auto_start_creo": False}, {"creo_session_id": "selected"}):
            with self.subTest(values=values), patch.dict(self.fixture.config, values):
                controller = self.controller()
                controller.start(retry=True)
                self.finish(controller)
                self.assertEqual(self.path.read_bytes(), self.raw)
        self.boot_query.assert_not_called()
        self.fixture.launch.assert_not_called()

    def test_archive_sync_failure_preserves_source(self):
        with patch("creo_mechdog.startup_state.os.fsync", side_effect=OSError("flush failed")):
            with self.assertRaises(OSError):
                archive_preboot_state(self.path, self.boot)
        self.assertEqual(self.path.read_bytes(), self.raw)

    def test_durable_json_is_flushed_before_atomic_replacement(self):
        original_replace = bridge._replace_json
        with patch.object(bridge.os, "fsync", wraps=bridge.os.fsync) as synced:

            def replace(temp, target):
                synced.assert_called_once()
                self.assertEqual(json.loads(temp.read_text()), {"state": "test"})
                original_replace(temp, target)

            with patch.object(bridge, "_replace_json", side_effect=replace):
                bridge.write_json(self.path, {"state": "test"}, durable=True)

    def test_failed_durable_json_flush_does_not_replace_existing_state(self):
        with patch.object(bridge.os, "fsync", side_effect=OSError("flush failed")):
            with self.assertRaises(OSError):
                bridge.write_json(self.path, {"state": "test"}, durable=True)
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertFalse(list(self.fixture.coordinator.glob("*.tmp")))


class WindowsBootEvidence(unittest.TestCase):
    def test_provider_result_requires_uptime_agreement(self):
        now = datetime.now(timezone.utc)
        started = now - timedelta(hours=1)
        result = Mock(stdout=started.isoformat().encode("ascii"))
        kernel = Mock()
        kernel.GetTickCount64.return_value = 3600 * 1000
        with (
            patch.object(windows_boot.subprocess, "run", return_value=result) as run,
            patch.object(windows_boot.ctypes, "WinDLL", return_value=kernel),
            patch.object(windows_boot, "datetime", wraps=datetime) as clock,
        ):
            clock.now.return_value = now
            self.assertIsNotNone(windows_boot.boot_info())
            self.assertEqual(run.call_args.kwargs["timeout"], 5)
            kernel.GetTickCount64.return_value = 3597 * 1000
            self.assertIsNone(windows_boot.boot_info())
            kernel.GetTickCount64.return_value = 10 * 1000
            self.assertIsNone(windows_boot.boot_info())

    def test_unavailable_or_malformed_boot_provider_cannot_authorize_recovery(self):
        for outcome in (
            subprocess.TimeoutExpired("boot query", 5),
            subprocess.CalledProcessError(1, "boot query"),
            Mock(stdout=b"not-a-timestamp"),
        ):
            with self.subTest(outcome=outcome), contextlib.ExitStack() as stack:
                if isinstance(outcome, Exception):
                    stack.enter_context(
                        patch.object(windows_boot.subprocess, "run", side_effect=outcome)
                    )
                else:
                    stack.enter_context(
                        patch.object(windows_boot.subprocess, "run", return_value=outcome)
                    )
                self.assertIsNone(windows_boot.boot_info())


if __name__ == "__main__":
    unittest.main()

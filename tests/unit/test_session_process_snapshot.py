"""DEV-036: session probes must expose Creo process identities (read-only)."""

import unittest
from datetime import datetime, timezone

import bridge
from tests.test_creo_startup import CreoStartupTests

_EPOCH_1601 = datetime(1601, 1, 1, tzinfo=timezone.utc)
_STAMP = datetime(2022, 2, 22, 22, 22, 22, tzinfo=timezone.utc)
_STAMP_FILETIME = (_STAMP - _EPOCH_1601).days * 86400 * 10**7 + (
    (_STAMP - _EPOCH_1601).seconds * 10**7
)


def failure():
    return {
        "connected": False,
        "connection_state": "not_found_or_unreadable",
        "toolkit_code": -4,
        "worker_exit_code": 20,
    }


class SessionProcessSnapshot(unittest.TestCase):
    def setUp(self):
        self.fixture = CreoStartupTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.startup = self.fixture.startup
        self.probe = self.fixture.probe
        self.inventory = self.fixture.inventory
        self.config = self.fixture.config

    def test_failed_probe_with_live_processes_distinguishes_dead_endpoint(self):
        self.probe.return_value = failure()
        self.inventory.return_value = {
            "processes": [
                {
                    "pid": 18720,
                    "created": _STAMP_FILETIME,
                    "image": str(self.fixture.creo / "Parametric/bin/parametric.exe"),
                    "matches": True,
                }
            ],
            "uncertain": False,
        }
        result = self.startup.session_status()
        self.assertFalse(result["connected"])
        snapshot = result["creo_process_snapshot"]
        self.assertTrue(snapshot["available"])
        self.assertEqual(snapshot["processes"][0]["pid"], 18720)
        self.assertTrue(snapshot["processes"][0]["matches"])
        self.assertEqual(snapshot["processes"][0]["created_at"], "2022-02-22T22:22:22+00:00")

    def test_failed_probe_without_processes_shows_no_creosession(self):
        self.probe.return_value = failure()
        result = self.startup.session_status()
        self.assertFalse(result["connected"])
        snapshot = result["creo_process_snapshot"]
        self.assertTrue(snapshot["available"])
        self.assertEqual(snapshot["processes"], [])

    def test_inventory_failure_keeps_probe_result_and_reports_reason(self):
        self.probe.return_value = failure()
        self.inventory.side_effect = OSError("denied")
        result = self.startup.session_status()
        self.assertFalse(result["connected"])
        self.assertEqual(
            result["creo_process_snapshot"],
            {"available": False, "reason": "inventory_failed_OSError"},
        )

    def test_configuration_error_still_returns_probe_failure(self):
        self.probe.return_value = failure()
        self.config["creo_root"] = 12
        result = self.startup.session_status()
        self.assertFalse(result["connected"])
        self.assertEqual(result["connection_state"], "not_found_or_unreadable")
        self.assertFalse(result["creo_process_snapshot"]["available"])
        self.assertIn("configuration_error", result["creo_process_snapshot"]["reason"])

    def test_busy_probe_includes_snapshot_and_startup(self):
        busy = bridge.ToolkitBusy(
            "busy",
            holder={"job_id": "j" * 32, "model_id": None, "operation": "execute_plan"},
        )
        self.probe.side_effect = busy
        result = self.startup.session_status()
        self.assertEqual(result["connection_state"], "busy")
        self.assertTrue(result["creo_process_snapshot"]["available"])
        self.assertIn("startup", result)

    def test_successful_probe_also_carries_snapshot(self):
        self.probe.return_value = {
            "connected": True,
            "connection_state": "connected",
            "toolkit_code": 0,
        }
        result = self.startup.session_status()
        self.assertTrue(result["connected"])
        self.assertTrue(result["creo_process_snapshot"]["available"])

    def test_running_coordinator_path_is_unchanged(self):
        self.startup._thread = type("T", (), {"is_alive": staticmethod(lambda: True)})()
        result = self.startup.session_status()
        self.assertNotIn("creo_process_snapshot", result)
        self.assertIn("startup", result)


if __name__ == "__main__":
    unittest.main()

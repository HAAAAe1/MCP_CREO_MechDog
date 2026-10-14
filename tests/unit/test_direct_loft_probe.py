"""Safety regressions for the BUG-007 developer reproduction runner."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from tools.test_direct_loft import Probe, UncertainOutcome


def response(value):
    return SimpleNamespace(is_error=False, structured_content=value)


class DirectLoftProbeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.client = SimpleNamespace(call_tool=AsyncMock())
        self.report = {"calls": [], "jobs": []}
        self.probe = Probe(self.client, self.report, Path(self.directory.name) / "evidence.json", 2)

    async def test_unknown_terminal_stops_all_subsequent_submissions(self):
        terminal = {"status": "unknown_outcome", "message": "worker timed out"}
        self.client.call_tool.side_effect = [
            response({"job_id": "probe_unknown"}),
            response(terminal),
            response(terminal),
        ]
        with self.assertRaises(UncertainOutcome):
            await self.probe.job("creo_loft", {"sections": ["sk_a", "sk_b"]}, "direct")
        count = self.client.call_tool.call_count
        with self.assertRaises(UncertainOutcome):
            await self.probe.job("creo_execute_plan", {}, "next_write")
        self.assertEqual(self.client.call_tool.call_count, count)
        self.assertEqual(self.report["jobs"][0]["terminal"], terminal)
        self.assertEqual(self.client.call_tool.call_args_list[1].args[1]["job_id"], "probe_unknown")

    async def test_lost_submit_response_does_not_resubmit(self):
        self.client.call_tool.side_effect = TimeoutError("response lost")
        with self.assertRaises(TimeoutError):
            await self.probe.job("creo_loft", {}, "direct")
        self.assertTrue(self.probe.uncertain)
        self.assertEqual(self.client.call_tool.call_count, 1)
        self.assertIn("transport_error", self.report["calls"][0])
        with self.assertRaises(UncertainOutcome):
            await self.probe.job("creo_loft", {}, "retry")
        self.assertEqual(self.client.call_tool.call_count, 1)

    async def test_observation_timeout_preserves_running_state(self):
        self.probe.job_budget = 0
        self.client.call_tool.return_value = response({"job_id": "still_running"})
        with self.assertRaises(UncertainOutcome):
            await self.probe.job("creo_loft", {}, "direct")
        self.assertIsNone(self.report["jobs"][0]["terminal"])
        self.assertTrue(self.probe.uncertain)
        self.assertEqual(self.client.call_tool.call_count, 1)

    async def test_failed_native_result_and_raw_error_are_preserved(self):
        terminal = {"status": "failed", "result": {"toolkit_code": -1, "rollback_succeeded": True}}
        self.client.call_tool.side_effect = [
            response({"job_id": "confirmed_failed"}),
            response(terminal),
            response(terminal),
        ]
        state = await self.probe.job("creo_loft", {}, "direct", expected_failure=True)
        self.assertEqual(state, terminal)
        self.assertFalse(self.probe.uncertain)
        self.assertEqual(self.report["jobs"][0]["terminal"]["result"]["toolkit_code"], -1)

    async def test_mutation_success_requires_save_reload_verification(self):
        terminal = {"status": "succeeded", "result": {"saved_file_reloaded_and_verified": False}}
        self.client.call_tool.side_effect = [
            response({"job_id": "unverified_success"}),
            response(terminal),
            response(terminal),
        ]
        with self.assertRaises(AssertionError):
            await self.probe.job("creo_loft", {}, "direct")
        self.assertEqual(self.report["jobs"][0]["terminal"], terminal)

    async def test_readonly_refresh_does_not_require_a_new_saved_file(self):
        terminal = {"status": "succeeded", "result": {"saved_file_reloaded_and_verified": False}}
        self.client.call_tool.side_effect = [
            response({"job_id": "readonly_refresh"}),
            response(terminal),
            response(terminal),
        ]
        state = await self.probe.job("creo_refresh_model", {}, "refresh")
        self.assertEqual(state, terminal)
        self.assertFalse(self.probe.uncertain)


if __name__ == "__main__":
    unittest.main()

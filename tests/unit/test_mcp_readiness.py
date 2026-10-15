"""Integration admission must never turn a startup failure into a mutation."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tools.mcp_readiness import wait_for_startup


def reply(state, connected=False):
    return SimpleNamespace(
        is_error=False, structured_content={"state": state, "connected": connected}
    )


class MCPReadinessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "evidence.json"
        self.client = SimpleNamespace(call_tool=AsyncMock())

    async def test_waits_for_verified_ready_using_only_public_read_queries(self):
        self.client.call_tool.side_effect = [reply("building_worker"), reply("ready", True)]
        report = {}
        with patch("tools.mcp_readiness.asyncio.sleep", new=AsyncMock()):
            result = await wait_for_startup(self.client, report, self.output)
        self.assertTrue(result["connected"])
        self.assertEqual(len(report["startup_queries"]), 2)
        for call in self.client.call_tool.call_args_list:
            self.assertEqual(call.args, ("creo_startup_status", {}))

    async def test_terminal_failure_and_unverified_ready_never_retry_or_submit(self):
        for state in ("timeout", "ready", "selection_required"):
            with self.subTest(state=state):
                self.client.call_tool.reset_mock(side_effect=True)
                self.client.call_tool.return_value = reply(state)
                with self.assertRaises(RuntimeError):
                    await wait_for_startup(self.client, {}, self.output)
                self.assertEqual(self.client.call_tool.call_count, 1)

    async def test_observation_timeout_preserves_raw_startup_and_does_not_force_retry(self):
        self.client.call_tool.return_value = reply("checking")
        report = {}
        with patch("tools.mcp_readiness.time.monotonic", side_effect=[0, 2]):
            with self.assertRaises(TimeoutError):
                await wait_for_startup(self.client, report, self.output, budget=1)
        self.assertEqual(report["startup"]["state"], "checking")
        self.assertEqual(self.client.call_tool.call_count, 1)


if __name__ == "__main__":
    unittest.main()

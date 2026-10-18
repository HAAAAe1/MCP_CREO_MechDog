"""DEV-040 persistent harness: real MCP transport, no Toolkit or Creo."""

import asyncio
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import bridge
import generic_bridge as general
from tools import dev040_blackbox_fixture as fixture


class FixtureRoot(unittest.TestCase):
    def setUp(self):
        fixture.FIXTURE_HOME.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="unit-", dir=fixture.FIXTURE_HOME)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "data"
        self.manifest = fixture.prepare(self.directory)

    def test_prepare_is_fresh_and_client_configuration_is_explicit(self):
        before = (self.directory / "fixtures.json").read_bytes()
        with self.assertRaises(FileExistsError):
            fixture.prepare(self.directory)
        self.assertEqual((self.directory / "fixtures.json").read_bytes(), before)
        with self.assertRaises(ValueError):
            fixture.checked_root(fixture.ROOT)
        config = json.loads((self.directory / "client-config.json").read_text(encoding="utf-8"))
        self.assertEqual(list(config["mcpServers"]), ["MCP_CREO_MechDog_dev"])
        connection = config["mcpServers"]["MCP_CREO_MechDog_dev"]
        self.assertEqual(connection["command"], sys.executable)
        self.assertEqual(connection["args"][:2], ["-m", "tools.dev040_blackbox_fixture"])
        self.assertEqual(Path(connection["cwd"]), fixture.ROOT)

    def test_firewall_blocks_build_session_and_arbitrary_processes(self):
        actual_root, actual_jobs, actual_models = bridge.ROOT, bridge.JOBS, general.MODELS
        with fixture.isolated(self.directory):
            self.assertEqual(bridge.ROOT, self.directory)
            self.assertEqual(bridge.JOBS, self.directory / "jobs")
            self.assertEqual(general.MODELS, self.directory / "models")
            for function, arguments in (
                (bridge.build_native, ()),
                (bridge.session_status, ()),
                (bridge.native_environment, ()),
                (subprocess.run, ([sys.executable, "-c", "raise AssertionError"],)),
                (subprocess.Popen, ([sys.executable, "-m", "server"],)),
            ):
                with self.subTest(function=function):
                    with self.assertRaisesRegex(RuntimeError, "fixture firewall"):
                        function(*arguments)
        self.assertEqual(
            (bridge.ROOT, bridge.JOBS, general.MODELS), (actual_root, actual_jobs, actual_models)
        )


class FixtureProtocol(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture.FIXTURE_HOME.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="stdio-unit-", dir=fixture.FIXTURE_HOME)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "data"
        self.manifest = fixture.prepare(self.directory)

    def client(self):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters

        return Client(
            StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "tools.dev040_blackbox_fixture",
                    "--serve",
                    "--data-root",
                    str(self.directory),
                ],
                cwd=str(fixture.ROOT),
            ),
            read_timeout_seconds=60,
        )

    async def call(self, client, name, arguments, *, error=False):
        reply = await client.call_tool(name, arguments)
        self.assertEqual(bool(reply.is_error), error, reply)
        return reply

    async def value(self, client, name, arguments):
        return (await self.call(client, name, arguments)).structured_content

    async def poll(self, client, job_id):
        for _ in range(80):
            result = await self.value(
                client, "creo_get_job", {"job_id": job_id, "detail": "compact"}
            )
            if result["status"] not in ("queued", "running"):
                return result
            await asyncio.sleep(0.2)
        self.fail(f"Fixture recovery did not finish: {job_id}")

    async def test_public_identity_nullable_schema_and_native_tools_blocked(self):
        async with self.client() as client:
            listed = await client.list_tools()
            self.assertEqual({tool.name for tool in listed.tools}, set(fixture.TOOLS))
            schema = next(
                tool.input_schema for tool in listed.tools if tool.name == "creo_reconcile_model"
            )
            self.assertIn(
                {"type": "null"}, schema["properties"]["expected_pending_job_id"]["anyOf"]
            )
            capability = await self.value(client, "creo_capabilities", {})
            self.assertEqual(capability["fixture_mode"], fixture.MODE)
            self.assertFalse(capability["actual_creo_verified"])
            self.assertEqual(capability["tool_count"], 4)
            for key, expected in (
                ("data_root", self.directory),
                ("job_root", self.directory / "jobs"),
                ("model_root", self.directory / "models"),
                ("lock_root", self.directory),
            ):
                self.assertEqual(Path(capability["runtime"][key]), expected)
            self.assertFalse(capability["runtime"]["fixture_source_changed"])
            for name in ("creo_session_status", "creo_new_part", "creo_check_environment"):
                await self.call(client, name, {}, error=True)
            await self.call(
                client,
                "creo_reconcile_model",
                {"model_id": self.manifest["items"][0]["model_id"], "live": True},
                error=True,
            )
            jobs = await self.value(client, "creo_list_jobs", {})
            self.assertEqual(len(jobs["jobs"]), 3)
        self.assertFalse((self.directory / "build").exists())

    async def test_rejection_unknown_success_idempotency_and_audit_over_stdio(self):
        originals = {
            item["original_job_id"]: (
                self.directory / "jobs" / item["original_job_id"] / "job.json"
            ).read_bytes()
            for item in self.manifest["items"]
        }
        async with self.client() as client:
            for index, item in enumerate(self.manifest["items"]):
                mid = item["model_id"]
                evidence = await self.value(client, "creo_reconcile_model", {"model_id": mid})
                self.assertTrue(evidence["actions"]["abandon_new"]["available"], evidence)
                arguments = {
                    "model_id": mid,
                    "mode": "apply",
                    "action": "abandon_new",
                    "expected_revision": evidence["revision"],
                    "evidence_token": evidence["evidence_token"],
                    "idempotency_key": f"dev040_fixture_contract_{index}",
                }
                if index != 2:
                    arguments["expected_pending_job_id"] = evidence["pending_job"]
                if index == 0:
                    rejected = await self.call(
                        client,
                        "creo_reconcile_model",
                        {**arguments, "expected_pending_job_id": ""},
                        error=True,
                    )
                    self.assertIn("expected_pending_job_id", str(rejected))
                created = await self.value(client, "creo_reconcile_model", arguments)
                compact = await self.poll(client, created["job_id"])
                full = await self.value(
                    client, "creo_get_job", {"job_id": created["job_id"], "detail": "full"}
                )
                replay = await self.value(client, "creo_reconcile_model", arguments)
                for key in (
                    "job_id",
                    "status",
                    "stage",
                    "reason",
                    "failure_phase",
                    "recovery_pending_released",
                ):
                    self.assertEqual(compact.get(key), full.get(key), key)
                    self.assertEqual(compact.get(key), replay.get(key), key)
                after = await self.value(client, "creo_reconcile_model", {"model_id": mid})
                self.assertEqual(after["revision"], evidence["revision"])
                self.assertEqual(after["pending_job"], evidence["pending_job"])
                job_dir = self.directory / "jobs" / created["job_id"]
                if index == 0:
                    self.assertEqual(compact["status"], "failed", full)
                    self.assertEqual(compact["stage"], "reconciliation_refused")
                    self.assertEqual(compact["reason"], "session_selection_changed")
                    self.assertEqual(compact["failure_phase"], "before_native")
                    self.assertTrue(compact["recovery_pending_released"])
                    self.assertIsNone(after["recovery_pending"])
                    self.assertEqual(after["status"], evidence["status"])
                    self.assertFalse((job_dir / "native_result.json").exists())
                elif index == 1:
                    self.assertEqual(compact["status"], "unknown_outcome", full)
                    self.assertEqual(compact["stage"], "reconciliation_unconfirmed")
                    self.assertEqual(compact["failure_phase"], "native_worker_started")
                    self.assertFalse(compact["recovery_pending_released"])
                    self.assertEqual(after["recovery_pending"], created["job_id"])
                    self.assertEqual(after["status"], evidence["status"])
                    self.assertTrue(full["result"]["synthetic_native_result"])
                    self.assertFalse(full["result"]["actual_native_worker_started"])
                else:
                    self.assertEqual(compact["status"], "succeeded", full)
                    self.assertEqual(after["status"], "abandoned")
                    self.assertIsNone(after["recovery_pending"])
                self.assertIn("finished_at", full)
            jobs = await self.value(client, "creo_list_jobs", {"limit": 20})
            self.assertEqual(len(jobs["jobs"]), 6, "Replay must not create another runner/job")
        for jid, original in originals.items():
            self.assertEqual((self.directory / "jobs" / jid / "job.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

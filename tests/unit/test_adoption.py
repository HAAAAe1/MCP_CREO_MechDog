"""FEAT-042: managed-copy adoption over the real stdio MCP protocol.

Every MCP case drives the actual tool registration, published schema and stdio
transport. The native boundary is substituted in the child processes only:
``adoption._native`` returns a synthetic probe/apply result so this file never
connects Toolkit, builds or opens Creo. Process-level cases additionally pin
``bridge.build_native``. All jobs/models/locks live in a temporary data root.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

import bridge
import generic_bridge as general
from creo_mechdog import adoption
from creo_mechdog import reconciliation as rec

INSPECTION = {
    "healthy": True,
    "features": [],
    "surfaces": [],
    "edges": [],
    "bodies": [],
    "datum_planes": [],
    "parameters": {},
    "volume_mm3": 10,
    "model_type": "part",
}


def _write(file: Path, value: dict) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value), encoding="utf-8")


def prepare_root(directory: Path) -> Path:
    (directory / "jobs").mkdir()
    (directory / "models").mkdir()
    source = directory / "user_parts"
    source.mkdir()
    part = source / "001.prt"
    part.write_bytes(b"fixture user part bytes 001")
    _write(
        directory / "config.json",
        {"creo_root": "C:\\feat042-fixture-creo", "vcvars64": "C:\\feat042-vcvars64.bat"},
    )
    return directory


def synthetic_native(job_directory: Path, manifest: dict) -> dict:
    """Fixture replacement for adoption._native; labeled substitution."""
    request = bridge.read_json(job_directory / "request.json")
    choice = request.get("adoption", {})
    manifest["worker_started"] = False
    manifest.update(stage="adopting_native_model", status="running")
    bridge.write_json(job_directory / "job.json", manifest, durable=True)
    manifest["worker_started"] = True
    bridge.write_json(job_directory / "job.json", manifest, durable=True)
    # The real worker persists its process identity; mirror a dead one so
    # recovery ownership checks can prove the synthetic worker stopped.
    _write(
        job_directory / "native_owner.json",
        {"pid": 2147483645, "created": 14},
    )
    result = {"connected": True, "delivery_complete": True, "disconnect_code": 0}
    if choice.get("action") == "inspect":
        result.update(
            success=True,
            live={
                "origin": str(bridge.ROOT / "user_parts" / "001.prt"),
                "model_type": "part",
                "healthy": True,
                "millimeter_units": True,
                "dependency_free": True,
                "session_fingerprint": "feat042-fixture-session",
                "inspection": INSPECTION,
            },
        )
    elif request["model"]["model_name"].startswith("fail"):
        result.update(
            success=False,
            failed_stage="adoption_apply",
            message="synthetic adoption failure; no Toolkit call",
        )
        bridge.write_json(job_directory / "native_result.json", result)
        manifest["result"] = result
        raise RuntimeError(result["message"])
    else:
        model = request["model"]
        part = Path(model["output_directory"]) / f"{model['model_name']}.prt.1"
        part.write_bytes(f"adopted managed copy {model['model_name']}".encode())
        result.update(
            success=True,
            saved_file_reloaded_and_verified=True,
            inspection=INSPECTION,
            aliases={},
            part_file=str(part),
            message="synthetic adoption fixture; no Toolkit call",
        )
    bridge.write_json(job_directory / "native_result.json", result)
    return result


def child_serve(directory: Path) -> None:
    import server

    bridge.ROOT = directory
    bridge.JOBS = directory / "jobs"
    general.MODELS = directory / "models"
    real_popen = subprocess.Popen

    def route(command, *args, **kwargs):
        if (
            isinstance(command, list)
            and len(command) == 4
            and Path(command[1]).name == "bridge.py"
            and command[2] == "run-job"
        ):
            command = [
                command[0],
                "-m",
                "tests.unit.test_adoption",
                "--data-root",
                str(directory),
                "--run-job",
                command[3],
            ]
            kwargs["cwd"] = ROOT
        return real_popen(command, *args, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.object(subprocess, "Popen", side_effect=route))
        stack.enter_context(patch.object(server.startup, "start"))
        stack.enter_context(patch.object(server.updates, "start"))
        stack.enter_context(
            patch.object(bridge, "build_native", return_value=directory / "worker.exe")
        )
        stack.enter_context(patch.object(adoption, "_native", side_effect=synthetic_native))
        # reconcile inspect (used by the failure-path test) binds deployment
        # identity against repository files that do not exist in the data root.
        stack.enter_context(
            patch.object(rec, "_deployment", return_value="feat042-fixture-deployment")
        )
        server.mcp.run()


def child_run_job(directory: Path, job_id: str) -> None:
    bridge.ROOT = directory
    bridge.JOBS = directory / "jobs"
    general.MODELS = directory / "models"
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(bridge, "build_native", return_value=directory / "worker.exe")
        )
        stack.enter_context(patch.object(adoption, "_native", side_effect=synthetic_native))
        bridge.run_job(job_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="FEAT-042 adoption protocol fixture child")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--run-job")
    args = parser.parse_args()
    if args.serve:
        child_serve(args.data_root)
    elif args.run_job:
        child_run_job(args.data_root, args.run_job)


class AdoptionMcpContract(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="feat042_protocol_")
        cls.directory = prepare_root(Path(cls.temporary.name))

    @classmethod
    def tearDownClass(cls):
        for survivor in ("toolkit.lock", "toolkit-owner.lock"):
            (cls.directory / survivor).unlink(missing_ok=True)
        cls.temporary.cleanup()

    def client(self):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters

        return Client(
            StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "tests.unit.test_adoption",
                    "--data-root",
                    str(self.directory),
                    "--serve",
                ],
                cwd=str(ROOT),
            ),
            read_timeout_seconds=90,
        )

    async def call(self, client, tool: str, arguments: dict, error: bool = False):
        reply = await client.call_tool(tool, arguments)
        self.assertEqual(bool(reply.is_error), error, reply)
        return reply.structured_content

    async def error_text(self, client, arguments: dict) -> str:
        reply = await client.call_tool("creo_adopt_current_model", arguments)
        self.assertTrue(reply.is_error, reply)
        return " ".join(block.text for block in reply.content if hasattr(block, "text"))

    async def poll(self, client, job_id: str) -> dict:
        for _ in range(90):
            result = await self.call(
                client, "creo_get_job", {"job_id": job_id, "detail": "compact"}
            )
            if result["status"] not in ("queued", "running"):
                return result
            await asyncio.sleep(0.4)
        self.fail(f"adoption job {job_id} never reached a terminal state")

    def model_file(self, model_id: str) -> dict:
        return json.loads(
            (self.directory / "models" / model_id / "model.json").read_text(encoding="utf-8")
        )

    def reset_registry(self) -> None:
        """Each MCP test adopts the same fixture source from a clean registry."""
        import shutil

        for child in (self.directory / "models").iterdir():
            shutil.rmtree(child, ignore_errors=True)

    def source_file(self) -> Path:
        return (self.directory / "user_parts" / "001.prt").resolve()

    async def test_tool_is_published_with_two_modes(self):
        self.reset_registry()
        async with self.client() as client:
            result = await client.list_tools()
            tool = next(t for t in result.tools if t.name == "creo_adopt_current_model")
            schema = json.dumps(tool.input_schema)
        self.assertIn("inspect", schema)
        self.assertIn("apply", schema)
        self.assertIn("idempotency_key", schema)

    async def test_inspect_apply_idempotent_replay_and_managed_copy(self):
        self.reset_registry()
        async with self.client() as client:
            evidence = await self.call(client, "creo_adopt_current_model", {})
            self.assertTrue(evidence["available"], evidence)
            self.assertEqual(evidence["status"], "adopt_pending")
            self.assertTrue(evidence["evidence_token"])
            self.assertEqual(evidence["file"]["path"], str(self.source_file()))
            model_id = evidence["model_id"]
            registered = self.model_file(model_id)
            self.assertEqual(registered["status"], "adopt_pending")
            self.assertEqual(registered["model_type"], "part")
            created = await self.call(
                client,
                "creo_adopt_current_model",
                {
                    "mode": "apply",
                    "model_id": model_id,
                    "evidence_token": evidence["evidence_token"],
                    "model_name": "feat042_managed",
                    "idempotency_key": "feat042_apply_once",
                },
            )
            job_id = created["job_id"]
            result = await self.poll(client, job_id)
            self.assertEqual(result["status"], "succeeded", result)
            after = self.model_file(model_id)
            self.assertEqual(after["status"], "ready")
            self.assertEqual(after["revision"], 1)
            self.assertEqual(after["model_name"], "feat042_managed")
            self.assertEqual(after["adopted_from"]["origin"], str(self.source_file()))
            self.assertEqual(after["adopted_from"]["adoption_id"], job_id)
            part = Path(after["part_file"])
            self.assertEqual(part.parent, Path(after["output_directory"]))
            self.assertEqual(after["part_sha256"], hashlib.sha256(part.read_bytes()).hexdigest())
            # The source file was never rewritten.
            self.assertEqual(
                (self.directory / "user_parts" / "001.prt").read_bytes(),
                b"fixture user part bytes 001",
            )
            replay = await self.call(
                client,
                "creo_adopt_current_model",
                {
                    "mode": "apply",
                    "model_id": model_id,
                    "evidence_token": evidence["evidence_token"],
                    "model_name": "feat042_managed",
                    "idempotency_key": "feat042_apply_once",
                },
            )
            self.assertEqual(replay["job_id"], job_id)

    async def test_apply_rejects_missing_and_invalid_inputs(self):
        self.reset_registry()
        async with self.client() as client:
            evidence = await self.call(client, "creo_adopt_current_model", {})
            model_id = evidence["model_id"]
            for arguments, fragment in (
                ({"mode": "apply"}, "model_id, evidence_token"),
                (
                    {
                        "mode": "apply",
                        "model_id": model_id,
                        "evidence_token": "0" * 32,
                        "idempotency_key": "feat042_bad_token",
                    },
                    "missing or expired",
                ),
                (
                    {
                        "mode": "apply",
                        "model_id": model_id,
                        "evidence_token": evidence["evidence_token"],
                        "model_name": "Bad-Name",
                        "idempotency_key": "feat042_bad_name",
                    },
                    "model_name",
                ),
            ):
                with self.subTest(fragment=fragment):
                    text = await self.error_text(client, arguments)
                    self.assertIn(fragment, text)

    async def test_repeated_inspect_of_same_source_reports_conflict(self):
        self.reset_registry()
        async with self.client() as client:
            first = await self.call(client, "creo_adopt_current_model", {})
            self.assertTrue(first["available"])
            created = await self.call(
                client,
                "creo_adopt_current_model",
                {
                    "mode": "apply",
                    "model_id": first["model_id"],
                    "evidence_token": first["evidence_token"],
                    "idempotency_key": "feat042_conflict_apply",
                },
            )
            self.assertEqual((await self.poll(client, created["job_id"]))["status"], "succeeded")
            second = await self.call(client, "creo_adopt_current_model", {})
            self.assertFalse(second["available"])
            self.assertEqual(second["conflict"]["reason"], "already_adopted")
            self.assertEqual(second["conflict"]["model_id"], first["model_id"])

    async def test_native_failure_keeps_adopt_pending_and_abandonable(self):
        self.reset_registry()
        async with self.client() as client:
            evidence = await self.call(client, "creo_adopt_current_model", {})
            model_id = evidence["model_id"]
            created = await self.call(
                client,
                "creo_adopt_current_model",
                {
                    "mode": "apply",
                    "model_id": model_id,
                    "evidence_token": evidence["evidence_token"],
                    "model_name": "fail_native",
                    "idempotency_key": "feat042_fail_once",
                },
            )
            result = await self.poll(client, created["job_id"])
            # The worker dispatch began, so the outcome stays protected exactly
            # like reconciliation: never a plain failure, never an auto-release.
            self.assertEqual(result["status"], "unknown_outcome", result)
            self.assertTrue(result["recovery_required"])
            after = self.model_file(model_id)
            self.assertEqual(after["status"], "adopt_pending")
            self.assertEqual(after["pending_job"], created["job_id"])
            # The failed registration resolves through the existing recovery tool
            # once the runner/worker can be proven stopped.
            for _ in range(20):
                reconcile_state = await self.call(
                    client, "creo_reconcile_model", {"model_id": model_id}
                )
                if reconcile_state["actions"]["abandon_new"]["available"]:
                    break
                await asyncio.sleep(0.5)
            else:
                self.fail("abandon_new never became available for the failed adoption")


class AdoptionBusinessRules(unittest.TestCase):
    """Process-level evidence guards against a synthetic native boundary."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="feat042_business_")
        self.directory = prepare_root(Path(self._temporary.name))
        real_root, real_jobs, real_models = bridge.ROOT, bridge.JOBS, general.MODELS
        bridge.ROOT = self.directory
        bridge.JOBS = self.directory / "jobs"
        general.MODELS = self.directory / "models"
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.callback(setattr, general, "MODELS", real_models)
        stack.callback(setattr, bridge, "JOBS", real_jobs)
        stack.callback(setattr, bridge, "ROOT", real_root)
        self.addCleanup(self._temporary.cleanup)
        stack.enter_context(
            patch.object(bridge, "build_native", return_value=self.directory / "worker.exe")
        )
        stack.enter_context(patch.object(adoption, "_native", side_effect=synthetic_native))

    def test_expired_evidence_is_refused(self):
        evidence = adoption.inspect()
        file = (
            general.model_path(evidence["model_id"])
            / "adoption"
            / f"evidence-{evidence['evidence_token']}.json"
        )
        record = json.loads(file.read_text(encoding="utf-8"))
        record["created"] -= adoption.TOKEN_SECONDS + 1
        _write(file, record)
        with self.assertRaisesRegex(ValueError, "expired"):
            adoption.apply(evidence["model_id"], evidence["evidence_token"], None, "feat042exp1")

    def test_changed_source_file_is_refused(self):
        evidence = adoption.inspect()
        (self.directory / "user_parts" / "001.prt").write_bytes(b"mutated after inspect")
        with self.assertRaisesRegex(ValueError, "changed since inspect"):
            adoption.apply(evidence["model_id"], evidence["evidence_token"], None, "feat042chg1")

    def test_modeling_submit_is_refused_while_adopt_pending(self):
        evidence = adoption.inspect()
        with self.assertRaisesRegex(ValueError, "not ready"):
            general.submit([{"op": "regenerate"}], evidence["model_id"], None, 0)
        self.assertEqual(self.model_json(evidence["model_id"])["status"], "adopt_pending")

    def model_json(self, model_id: str) -> dict:
        return json.loads(
            (self.directory / "models" / model_id / "model.json").read_text(encoding="utf-8")
        )

    def test_unsupported_types_are_refused_at_inspect(self):
        def unsupported(job_directory, manifest):
            result = synthetic_native(job_directory, manifest)
            result["live"] = {
                **result["live"],
                "model_type": "assembly",
                "dependency_free": False,
                "millimeter_units": False,
                "healthy": False,
            }
            return result

        with patch.object(adoption, "_native", side_effect=unsupported):
            evidence = adoption.inspect()
        self.assertFalse(evidence["available"])
        self.assertIn("part or sheetmetal", evidence["reason"])


if __name__ == "__main__":
    main()

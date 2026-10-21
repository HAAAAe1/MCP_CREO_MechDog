"""DEV-040 persistent, isolated MCP contract fixtures; never opens Creo.

Prepare a NEW root, then point only a dedicated WorkBuddy test connection at
its generated client-config.json. Native results and the build prerequisite
are explicitly substituted. This is Python/MCP contract evidence, not native
modeling or live Creo acceptance. stdout belongs to MCP when --serve is used.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
import uuid
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import reconciliation as rec

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_HOME = ROOT / "build/dev040-blackbox"
MODE = "dev040_isolated_mcp_contract_v1"
TOOLS = ("creo_capabilities", "creo_reconcile_model", "creo_get_job", "creo_list_jobs")
SCENARIOS = ("before_native_refusal", "synthetic_native_unknown", "synthetic_success")
STOPPED_OWNER = {"pid": 2147483647, "created": 1}
BOUNDARIES = [
    "Synthetic model/job records, stopped owner records, and no CAD files",
    "Deployment binding uses current fixture/Python source hashes, not native build identity",
    "Runner build prerequisite substituted with a nonexistent, nonexecutable marker",
    "A: runner-only session selection differs; real Python execution refusal runs",
    "B/C: reconciliation._native substituted; worker_started is synthetic, no worker exists",
]


def checked_root(directory: Path) -> Path:
    """Reject production roots, links and traversal outside the dedicated fixture area."""
    directory = directory.absolute()
    if any(item.is_symlink() or item.is_junction() for item in (directory, *directory.parents)):
        raise ValueError("Fixture data paths must not contain links or junctions")
    directory = directory.resolve()
    if FIXTURE_HOME.resolve() not in directory.parents:
        raise ValueError("Fixture data root must be a new child of build/dev040-blackbox")
    return directory


def deployment(_deadline: float) -> str:
    """Keep source changes visible while replacing the native deployment boundary."""
    return rec.digest(
        {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "bridge.py",
                "server.py",
                "src/creo_mechdog/reconciliation.py",
                "tools/dev040_blackbox_fixture.py",
            )
        }
    )


def prepare(directory: Path) -> dict:
    """Create only synthetic fixtures in a fresh root; never overwrite a prior run."""
    directory = checked_root(directory)
    if bridge.process_identity(STOPPED_OWNER["pid"]).get("alive") is not False:
        raise RuntimeError("Synthetic stopped PID cannot be proven absent on this host")
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "jobs").mkdir()
    (directory / "models").mkdir()
    bridge.write_json(
        directory / "config.json",
        {
            "creo_root": str(directory / "NO_CREO_INSTALLATION"),
            "vcvars64": str(directory / "NO_COMPILER.bat"),
        },
    )
    items = []
    for index, scenario in enumerate(SCENARIOS):
        mid, jid = uuid.uuid4().hex, uuid.uuid4().hex
        output = directory / "models" / mid / "output"
        output.mkdir(parents=True)
        model = {
            "model_id": mid,
            "model_name": f"dev040_fixture_{chr(97 + index)}",
            "model_type": "part",
            "revision": 0,
            "status": "unknown_outcome" if index == 1 else "failed",
            "aliases": {},
            "inspection": {},
            "output_directory": str(output),
            "part_file": None,
            "part_sha256": None,
            "last_job": jid,
            "pending_job": jid if index == 1 else None,
            "recovery_pending": None,
        }
        bridge.write_json(output.parent / "model.json", model)
        original = directory / "jobs" / jid
        original.mkdir()
        bridge.write_json(
            original / "job.json",
            {
                "job_id": jid,
                "model_id": mid,
                "kind": "generic",
                "status": model["status"],
                "created_at": bridge.now(),
                "runner_identity": STOPPED_OWNER,
                "fixture_mode": MODE,
            },
        )
        bridge.write_json(original / "request.json", {"model": model, "operations": []})
        bridge.write_json(original / "native_owner.json", STOPPED_OWNER)
        items.append(
            {"scenario": scenario, "model_id": mid, "original_job_id": jid, "action": "abandon_new"}
        )
    manifest = {
        "fixture_mode": MODE,
        "prepared_at": bridge.now(),
        "data_root": str(directory),
        "source_root": str(ROOT),
        "deployment_at_prepare": deployment(0),
        "synthetic_boundaries": BOUNDARIES,
        "actual_creo_verified": False,
        "allowed_tools": list(TOOLS),
        "items": items,
    }
    bridge.write_json(directory / "fixtures.json", manifest)
    bridge.write_json(
        directory / "client-config.json",
        {
            "mcpServers": {
                "MCP_CREO_MechDog_dev": {
                    "command": sys.executable,
                    "args": [
                        "-m",
                        "tools.dev040_blackbox_fixture",
                        "--serve",
                        "--data-root",
                        str(directory),
                    ],
                    "cwd": str(ROOT),
                }
            }
        },
    )
    return manifest


def load(directory: Path) -> dict:
    directory = checked_root(directory)
    manifest = bridge.read_json(directory / "fixtures.json")
    if manifest.get("fixture_mode") != MODE or manifest.get("data_root") != str(directory):
        raise ValueError("Not a prepared DEV-040 fixture root")
    for child in (directory / "jobs", directory / "models"):
        if child.is_symlink() or child.is_junction() or not child.is_dir():
            raise ValueError("Fixture jobs/models must be real directories")
    return manifest


def denied(*_args, **_kwargs):
    raise RuntimeError("DEV-040 fixture firewall: native/build/session/process execution disabled")


def runner_route(directory: Path, manifest: dict, real_popen):
    """Only an exact, owned recovery runner command may create a child process."""
    allowed_models = {item["model_id"] for item in manifest["items"]}

    def route(command, *args, **kwargs):
        if (
            not isinstance(command, list)
            or len(command) != 4
            or command[:3] != [sys.executable, str(directory / "bridge.py"), "run-job"]
            or not isinstance(command[3], str)
            or not bridge.JOB_ID.fullmatch(command[3])
            or args
            or set(kwargs) - {"cwd", "stdin", "stdout", "stderr", "creationflags", "close_fds"}
            or kwargs.get("stdin") != subprocess.DEVNULL
            or kwargs.get("stderr") != subprocess.STDOUT
            or kwargs.get("creationflags") != bridge.HIDDEN
            or kwargs.get("close_fds") is not True
            or Path(kwargs.get("cwd", ".")).resolve() != directory
        ):
            return denied()
        job_file = directory / "jobs" / command[3] / "job.json"
        job = bridge.read_json(job_file)
        if job.get("kind") != "reconciliation" or job.get("model_id") not in allowed_models:
            return denied()
        command = [
            sys.executable,
            "-m",
            "tools.dev040_blackbox_fixture",
            "--data-root",
            str(directory),
            "--run-job",
            command[3],
        ]
        return real_popen(command, **{**kwargs, "cwd": ROOT})

    return route


@contextmanager
def isolated(directory: Path, *, child: bool = False):
    """Route all runtime storage locally and prevent any real native dispatch."""
    manifest = load(directory)
    real_popen = subprocess.Popen
    with ExitStack() as stack:
        stack.enter_context(patch.object(bridge, "ROOT", directory))
        stack.enter_context(patch.object(bridge, "JOBS", directory / "jobs"))
        stack.enter_context(patch.object(general, "MODELS", directory / "models"))
        stack.enter_context(patch.object(rec, "_deployment", side_effect=deployment))
        # Synthetic records have no real boot history; never query host WMI here.
        stack.enter_context(patch.object(rec, "boot_info", return_value=None))
        for target in ("build_native", "session_status", "native_environment"):
            stack.enter_context(patch.object(bridge, target, side_effect=denied))
        stack.enter_context(patch.object(rec, "_native", side_effect=denied))
        stack.enter_context(patch.object(rec, "_live", side_effect=denied))
        for name in ("run", "call", "check_call", "check_output"):
            stack.enter_context(patch.object(subprocess, name, side_effect=denied))
        stack.enter_context(
            patch.object(
                subprocess,
                "Popen",
                side_effect=denied if child else runner_route(directory, manifest, real_popen),
            )
        )
        yield manifest


def synthetic_native(directory: Path, manifest: dict, scenario: str) -> dict:
    """Substitute only the native boundary; no native executable exists or runs."""
    if scenario == "before_native_refusal":
        raise AssertionError("Before-native fixture reached the forbidden native boundary")
    manifest.update(status="running", stage="reconciling_native_model", worker_started=True)
    bridge.write_json(directory / "job.json", manifest, durable=True)
    result = {
        "success": scenario == "synthetic_success",
        "fixture_mode": MODE,
        "synthetic_native_result": True,
        "actual_native_worker_started": False,
        "message": "Synthetic fixture result; no Toolkit or Creo call",
    }
    if scenario == "synthetic_native_unknown":
        result.update(
            failed_stage="recovery_abandon_new",
            message="Recovery refused: Creo session changed since recorded evidence",
        )
    bridge.write_json(directory / "native_result.json", result)
    manifest["result"] = result
    if not result["success"]:
        raise RuntimeError(result["message"])
    return result


def run_job(directory: Path, job_id: str) -> None:
    with isolated(directory, child=True) as manifest, ExitStack() as stack:
        job = bridge.read_json(bridge.job_path(job_id) / "job.json")
        item = next(item for item in manifest["items"] if item["model_id"] == job["model_id"])
        if job.get("kind") != "reconciliation" or job.get("action") != item["action"]:
            raise ValueError("Only the prepared recovery fixture action is permitted")
        # Production calls build_native before its execution checks. This marker
        # replaces that prerequisite; Popen/run remain forbidden in this child.
        stack.enter_context(
            patch.object(bridge, "build_native", return_value=directory / "NO_NATIVE_WORKER")
        )
        if item["scenario"] == "before_native_refusal":
            settings = {**bridge.config(), "creo_session_id": "dev040_fixture_changed"}
            stack.enter_context(patch.object(bridge, "config", return_value=settings))
        stack.enter_context(
            patch.object(
                rec,
                "_native",
                side_effect=lambda path, state: synthetic_native(path, state, item["scenario"]),
            )
        )
        bridge.run_job(job_id)


async def configure_server(directory: Path, manifest: dict) -> None:
    import server

    for tool in await server.mcp.list_tools():
        if tool.name not in TOOLS or tool.name == "creo_capabilities":
            server.mcp.remove_tool(tool.name)

    async def capabilities() -> dict[str, Any]:
        return {
            "name": "MCP_CREO_MechDog",
            "version": server.VERSION,
            "fixture_mode": MODE,
            "actual_creo_verified": False,
            "synthetic_boundaries": BOUNDARIES,
            "tool_count": len(TOOLS),
            "enabled_tool_count": len(TOOLS),
            "allowed_tools": list(TOOLS),
            "fixtures": manifest["items"],
            "scheduling": {
                "native_channels": 0,
                "fixture_lock_channels": 1,
                "admission": "reject_busy_without_creating_a_job",
                "scope": "Isolated fixture OS lock; real Toolkit channel not tested",
            },
            "runtime": {
                "python_executable": sys.executable,
                "code_root": str(ROOT),
                "python_package_root": str(server.SOURCE_PATHS.code_root),
                "resource_root": str(ROOT),
                "server_entry": str(Path(__file__).resolve()),
                "production_server_entry": str(ROOT / "server.py"),
                "data_root": str(directory),
                "job_root": str(directory / "jobs"),
                "model_root": str(directory / "models"),
                "lock_root": str(directory),
                "source_fingerprints_at_startup": dict(server._LOADED_FINGERPRINTS),
                "source_changed_since_startup": server._source_fingerprints()
                != server._LOADED_FINGERPRINTS,
                "fixture_deployment": deployment(0),
                "fixture_deployment_at_prepare": manifest["deployment_at_prepare"],
                "fixture_source_changed": deployment(0) != manifest["deployment_at_prepare"],
            },
            "not_verified": [
                "Creo connection/session fingerprint changes/interruption",
                "Geometry, native save/reload and rollback",
                "Production deployment binding, production shared lock and BUG-057 root cause",
                "Other Creo versions and unexecuted concurrent calls",
            ],
        }

    server.mcp.add_tool(capabilities, name="creo_capabilities", annotations=server.READ)
    server.mcp._lowlevel_server.instructions = (
        "DEV-040 ISOLATED MCP CONTRACT FIXTURE. No Creo connection, native geometry or real worker. "
        "Call creo_capabilities first for synthetic boundaries and dedicated model IDs. "
        "Use only listed fixture actions; poll accepted jobs; do not treat this as native acceptance."
    )


def serve(directory: Path) -> None:
    import server

    with isolated(directory) as manifest, ExitStack() as stack:
        stack.enter_context(patch.object(server.startup, "start"))
        stack.enter_context(patch.object(server.updates, "start"))
        asyncio.run(configure_server(directory, manifest))
        server.mcp.run()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--prepare", action="store_true")
    operation.add_argument("--serve", action="store_true")
    operation.add_argument("--run-job")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    if not args.prepare and args.data_root is None:
        parser.error("--serve/--run-job require a prepared --data-root")
    directory = checked_root(
        args.data_root or FIXTURE_HOME / f"run-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
    )
    if args.prepare:
        print(json.dumps(prepare(directory), ensure_ascii=False, indent=2))
    elif args.serve:
        serve(directory)
    else:
        run_job(directory, args.run_job)


if __name__ == "__main__":
    main()

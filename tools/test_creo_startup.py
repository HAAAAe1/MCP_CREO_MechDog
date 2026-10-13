"""FEAT-019 developer acceptance: MCP cold startup, coordination and native modeling."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and not __package__:
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "tools.test_creo_startup", *sys.argv[1:]], cwd=ROOT)
    )

from mcp import Client
from mcp.client.stdio import StdioServerParameters

import bridge
import creo_startup
from tools.dev_check import git_state, source_hash
from version import VERSION


async def call(client: Client, name: str, args: dict) -> dict:
    result = await client.call_tool(name, args)
    if result.is_error:
        raise RuntimeError(f"{name}: {result.content}")
    return result.structured_content


async def wait_ready(client: Client, trace: list, timeout: float = 360) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = await call(client, "creo_startup_status", {})
        if not trace or trace[-1]["state"] != status["state"]:
            trace.append({"elapsed_seconds": time.monotonic() - (deadline - timeout), **status})
            print(f"startup={status['state']} {status['message']}", flush=True)
        if status["state"] == "ready":
            assert status["connected"] is True
            return status
        if status["state"] not in creo_startup.ACTIVE:
            raise RuntimeError(f"Startup stopped: {status}")
        await asyncio.sleep(0.5)
    raise TimeoutError("MCP startup did not finish within the developer test budget")


async def job(client: Client, name: str, args: dict, report: dict) -> dict:
    created = await call(client, name, args)
    began = time.monotonic()
    while time.monotonic() - began < 720:
        result = await call(client, "creo_get_job", {"job_id": created["job_id"], "detail": "full"})
        if result["status"] not in ("queued", "running"):
            report["jobs"].append({"tool": name, "args": args, "job": result})
            assert result["status"] == "succeeded", result.get("message")
            assert result["result"]["saved_file_reloaded_and_verified"] is True
            return result
        await asyncio.sleep(0.5)
    raise TimeoutError(f"Modeling task {created['job_id']} did not finish")


async def run(args: argparse.Namespace) -> dict:
    settings = creo_startup.Settings.load()
    before = creo_startup.inventory(settings)
    if args.require_cold and (before["uncertain"] or before["processes"]):
        raise RuntimeError(
            "Cold test requires Creo already closed by the operator; this script never closes existing Creo"
        )
    report = {
        "work_item": "FEAT-019",
        "version": VERSION,
        "timestamp_utc": bridge.now(),
        "command": [sys.executable, *sys.argv],
        "source": {
            **git_state(ROOT),
            "fingerprints": {
                name: source_hash(ROOT / name)
                for name in (
                    "server.py",
                    "bridge.py",
                    "creo_startup.py",
                    "native/worker.cpp",
                    "tools/test_creo_startup.py",
                )
            },
        },
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "creo_root": str(settings.executable.parents[2]),
            "creo": "12.4.0.0"
            if "Creo 12.4" in str(settings.executable)
            else "see installation/release_numeric",
        },
        "initial_creo_process_count": len(before["processes"]),
        "initial_inventory_uncertain": before["uncertain"],
        "cold_start": not before["processes"] and not before["uncertain"],
        "clients": [],
        "jobs": [],
        "success": False,
    }
    parameters = StdioServerParameters(
        command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT
    )
    try:
        async with AsyncExitStack() as stack:
            began = time.monotonic()
            first = await stack.enter_async_context(Client(parameters, read_timeout_seconds=30))
            first_handshake = time.monotonic() - began
            if args.retry:
                # Let this first client's automatic recheck finish. Then request
                # retry explicitly before admitting a second startup contender.
                # This exercises coordinated waiting during the actual launch,
                # rather than confusing two independent old failure snapshots.
                retry_deadline = time.monotonic() + 360
                while time.monotonic() < retry_deadline:
                    initial = await call(first, "creo_startup_status", {})
                    if initial["state"] not in creo_startup.ACTIVE:
                        break
                    await asyncio.sleep(0.2)
                if initial["state"] != "ready":
                    await call(first, "creo_startup_status", {"retry": True})
                    while time.monotonic() < retry_deadline:
                        active = await call(first, "creo_startup_status", {})
                        if active["state"] != "checking":
                            break
                        await asyncio.sleep(0.05)
            began = time.monotonic()
            second = await stack.enter_async_context(Client(parameters, read_timeout_seconds=30))
            second_handshake = time.monotonic() - began
            report["handshake_seconds"] = [first_handshake, second_handshake]
            assert max(report["handshake_seconds"]) < 15, report["handshake_seconds"]
            tools = await first.list_tools()
            assert "creo_startup_status" in [tool.name for tool in tools.tools]
            admission = await call(first, "creo_startup_status", {})
            if report["cold_start"] and admission["state"] in creo_startup.ACTIVE:
                denied = await first.call_tool("creo_new_part", {})
                assert denied.is_error, "A modeling request before readiness must be rejected"
                report["modeling_before_ready"] = {
                    "startup_state": admission["state"],
                    "is_error": denied.is_error,
                    "content": [item.model_dump() for item in denied.content],
                }
            report["protocol_version"] = first.protocol_version
            traces = [[], []]
            ready = await asyncio.gather(
                wait_ready(first, traces[0]), wait_ready(second, traces[1])
            )
            report["clients"] = [
                {"trace": trace, "ready": state} for trace, state in zip(traces, ready)
            ]
            connected = await call(first, "creo_session_status", {})
            report["live_session"] = connected
            assert connected["connected"] is True
            after = creo_startup.inventory(settings)
            assert not after["uncertain"]
            xtop = [p for p in after["processes"] if Path(p["image"]).name.lower() == "xtop.exe"]
            report["creo_instance_count_after_startup"] = len(xtop)
            if report["cold_start"]:
                assert len(xtop) == 1, after
            # A third MCP service must reuse the verified instance.
            third = await stack.enter_async_context(Client(parameters, read_timeout_seconds=30))
            reuse_trace = []
            reuse = await wait_ready(third, reuse_trace)
            report["existing_session_reuse"] = {"trace": reuse_trace, "ready": reuse}
            assert reuse["launched_by_coordinator"] is False
            reused = [
                p
                for p in creo_startup.inventory(settings)["processes"]
                if Path(p["image"]).name.lower() == "xtop.exe"
            ]
            assert [(p["pid"], p["created"]) for p in xtop] == [
                (p["pid"], p["created"]) for p in reused
            ]
            report["no_duplicate_launch"] = True
            created = await job(
                first,
                "creo_execute_plan",
                {
                    "operations": [
                        {
                            "op": "sketch",
                            "label": "startup_profile",
                            "plane": "XY",
                            "entities": [
                                {
                                    "type": "rectangle",
                                    "name": "outline",
                                    "min": [-10, -5],
                                    "max": [10, 5],
                                }
                            ],
                        },
                        {
                            "op": "extrude",
                            "label": "startup_solid",
                            "sketch": "startup_profile",
                            "depth": 2,
                        },
                    ],
                    "assertions": {"volume_mm3": 400, "require_solid": True},
                },
                report,
            )
            assert abs(created["result"]["inspection"]["volume_mm3"] - 400) < 0.001
            assert created["revision"] == 1
            edited = await job(
                first,
                "creo_set_parameters",
                {
                    "model_id": created["model_id"],
                    "expected_revision": 1,
                    "values": {"STARTUP_SIZE": 17.0},
                },
                report,
            )
            assert edited["revision"] == 2
            model = await call(second, "creo_inspect_model", {"model_id": created["model_id"]})
            assert model["pending_job"] is None and model["revision"] == 2
            assert model["inspection"]["parameters"]["STARTUP_SIZE"]["value"] == 17.0
            assert abs(model["inspection"]["volume_mm3"] - 400) < 0.001
            report.update(
                model_id=created["model_id"],
                volume_mm3=model["inspection"]["volume_mm3"],
                parameter_verified=True,
                revision_correct=True,
                pending_job_cleared=True,
            )
        surviving = [
            p
            for p in creo_startup.inventory(settings)["processes"]
            if Path(p["image"]).name.lower() == "xtop.exe"
        ]
        report["session_survived_mcp_shutdown"] = [(p["pid"], p["created"]) for p in surviving] == [
            (p["pid"], p["created"]) for p in xtop
        ]
        assert report["session_survived_mcp_shutdown"], (
            "MCP shutdown must not terminate the Creo instance"
        )
        # Process survival alone does not prove the name service/Toolkit path
        # survived cleanup of the originating stdio host's Windows Job.
        async with Client(parameters, read_timeout_seconds=30) as reopened:
            trace = []
            ready = await wait_ready(reopened, trace)
            assert ready["launched_by_coordinator"] is False
            report["reconnect_after_all_clients_closed"] = {"trace": trace, "ready": ready}
            model = await call(reopened, "creo_inspect_model", {"model_id": created["model_id"]})
            assert model["revision"] == 2
            assert model["inspection"]["parameters"]["STARTUP_SIZE"]["value"] == 17.0
        report["success"] = True
    except Exception as exc:
        report["success"] = False
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-cold", action="store_true")
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Explicitly recheck a previous failed launch through the MCP retry tool",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "build/FEAT-019-startup.json")
    args = parser.parse_args()
    report = asyncio.run(run(args))
    for name in ("creo_worker.exe", "creo_blend_sync.dll"):
        path = ROOT / "build" / name
        if path.is_file():
            report[name + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"FEAT-019 startup validation: success={report['success']}; report={args.output}",
        flush=True,
    )
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

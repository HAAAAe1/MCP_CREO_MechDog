"""Real MCP plan-loft and callback admission checks for an operator-prepared phase.

Does not deploy, register, stop, restart, or replay modeling operations. A rejected
phase checks both public loft entry points before model mutation. This is developer
evidence, separate from WorkBuddy acceptance.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import platform
import sys
import time
from collections.abc import Coroutine
from datetime import datetime, timezone
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from tools.dev_check import git_state, source_hash
from tools.test_direct_loft import Probe, circle_sections, small_solid, verify_blend
from version import VERSION

ROOT = Path(__file__).resolve().parents[1]


async def check_busy(probe: Probe, operation: Coroutine[object, object, dict]) -> dict:
    """Observe an actual modeling job and issue a concurrent read-only query."""
    task = asyncio.create_task(operation)
    try:
        for _ in range(40):
            if task.done():
                break
            await asyncio.sleep(0.25)
            started = time.monotonic()
            status = await probe.call("creo_callback_status", {})
            if status.get("reason") == "channel_busy":
                assert status["readiness"] == "unknown"
                assert status["registration_status"] == "unknown"
                assert time.monotonic() - started < 2
                probe.report["busy_observed"] = True
                break
        # Always finish observing the submitted job before another write.
        return await task
    finally:
        if not task.done():
            await task


async def run(args: argparse.Namespace) -> dict:
    report = {
        "work_item": "FEAT-029",
        "version": VERSION,
        "phase": args.phase,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            **git_state(ROOT),
            "fingerprints": {
                p.relative_to(ROOT).as_posix(): source_hash(p)
                for p in [Path(__file__), ROOT / "native/blend_sync.cpp", ROOT / "bridge.py"]
            },
        },
        "environment": {"os": platform.platform(), "python": platform.python_version()},
        "calls": [],
        "jobs": [],
        "success": False,
        "busy_observed": False,
        "scope": "Developer real stdio MCP; not WorkBuddy or GUI lifecycle acceptance",
        "unverified": ["WorkBuddy", "Creo 10", "GUI registration actions"],
    }
    probe = None
    try:
        params = StdioServerParameters(
            command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT
        )
        async with Client(params, read_timeout_seconds=65) as client:
            probe = Probe(client, report, args.output, 900)
            startup = await probe.call("creo_startup_status", {})
            deadline = time.monotonic() + 130
            while (
                startup["state"]
                in {"checking", "building_worker", "starting", "waiting_for_connection"}
                and time.monotonic() < deadline
            ):
                await asyncio.sleep(1)
                startup = await probe.call("creo_startup_status", {})
            assert startup["state"] == "ready", startup
            cap = await probe.call("creo_capabilities", {})
            assert Path(cap["runtime"]["resource_root"]).resolve() == ROOT.resolve()
            status = await probe.call("creo_callback_status", {})
            assert status["readiness"] == args.expect, status
            report["callback"] = status
            for key in ("module_file", "loader_file", "registry_file"):
                path = Path(status[key])
                report.setdefault("artifacts", {})[key] = {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            if args.phase == "ready":
                for count, mode, solid in ((2, "straight", False), (3, "smooth", True)):
                    checkpoint = await probe.job(
                        "creo_execute_plan",
                        {"operations": (small_solid() if solid else []) + circle_sections(count)},
                        f"plan_{count}_{mode}_checkpoint",
                    )
                    state = await check_busy(
                        probe,
                        probe.job(
                            "creo_execute_plan",
                            {
                                "model_id": checkpoint["model_id"],
                                "expected_revision": checkpoint["revision"],
                                "operations": [
                                    {
                                        "op": "loft",
                                        "label": "blend_probe",
                                        "sections": [s["label"] for s in circle_sections(count)],
                                        "interpolation": mode,
                                    }
                                ],
                            },
                            f"plan_{count}_{mode}",
                        ),
                    )
                    verify_blend(
                        state,
                        count,
                        mode,
                        checkpoint,
                        4900 * math.pi / 3 if mode == "straight" else None,
                    )
                fresh = await probe.job(
                    "creo_execute_plan",
                    {
                        "operations": circle_sections()
                        + [
                            {
                                "op": "loft",
                                "label": "blend_probe",
                                "sections": ["sk_a", "sk_b"],
                                "interpolation": "straight",
                            }
                        ]
                    },
                    "single_plan_new_loft",
                )
                verify_blend(fresh, 2, "straight", expected_volume=4900 * math.pi / 3)
            else:
                checkpoint = await probe.job(
                    "creo_execute_plan", {"operations": circle_sections()}, "protected_checkpoint"
                )
                before = await probe.call(
                    "creo_inspect_model", {"model_id": checkpoint["model_id"]}
                )
                path = Path(checkpoint["result"]["part_file"])
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                loft = {
                    "label": "blend_probe",
                    "sections": ["sk_a", "sk_b"],
                    "interpolation": "straight",
                }
                for tool, extra in (
                    ("creo_loft", loft),
                    ("creo_execute_plan", {"operations": [{"op": "loft", **loft}]}),
                ):
                    state = await probe.job(
                        tool,
                        {
                            "model_id": checkpoint["model_id"],
                            "expected_revision": checkpoint["revision"],
                            **extra,
                        },
                        tool + "_preflight_rejected",
                        expected_failure=True,
                    )
                    assert "BLEND_CALLBACK_SETUP_REQUIRED" in state.get("message", ""), state
                    assert state["result"]["model_unchanged"] is True
                    assert state["result"]["rollback_succeeded"] is False
                    after = await probe.call(
                        "creo_inspect_model", {"model_id": checkpoint["model_id"]}
                    )
                    for key in ("revision", "part_file", "inspection", "aliases"):
                        assert after[key] == before[key], key
                    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
                    assert probe.report["jobs"][-1]["elapsed_seconds"] < 30
                failed_new = await probe.job(
                    "creo_execute_plan",
                    {
                        "operations": circle_sections() + [{"op": "loft", **loft}],
                    },
                    "new_plan_preflight_rejected",
                    expected_failure=True,
                )
                assert failed_new["result"]["model_unchanged"] is True
                await probe.job(
                    "creo_execute_plan",
                    {
                        "operations": small_solid(),
                        "assertions": {"volume_mm3": 2000},
                    },
                    "post_rejection_small_solid",
                )
            report["success"] = True
    except Exception as exc:
        report["failure"] = repr(exc)
        report["writes_stopped_for_uncertain_outcome"] = bool(probe and probe.uncertain)
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps({k: report.get(k) for k in ("success", "failure", "busy_observed")}),
            flush=True,
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["ready", "rejected"], required=True)
    parser.add_argument(
        "--expect", choices=["ready", "version_mismatch", "not_loaded", "unknown"], required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.phase == "ready") != (args.expect == "ready"):
        parser.error("ready phase requires ready; rejected phase requires a non-ready status")
    return 0 if asyncio.run(run(args))["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

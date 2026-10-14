"""BUG-006 developer stdio contract checks; --create adds real Creo axis-pattern acceptance."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and not __package__:
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "tools.test_reference_contract", *sys.argv[1:]], cwd=ROOT
        )
    )

from tools.dev_check import git_state, source_hash
from version import VERSION


async def run(args: argparse.Namespace) -> dict:
    report = {
        "work_item": "BUG-006",
        "version": VERSION,
        "source": {
            **git_state(ROOT),
            "fingerprints": {
                name: source_hash(ROOT / name)
                for name in (
                    "server.py",
                    "schema.py",
                    "src/creo_mechdog/references.py",
                    "tools/test_reference_contract.py",
                )
            },
        },
        "environment": {"os": platform.platform(), "python": platform.python_version()},
        "calls": [],
        "jobs": [],
        "protocol_verified": False,
        "native": "not_requested",
        "success": False,
    }
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)

    async def call(client, name, inputs, *, expect_error=False):
        started = time.monotonic()
        response = await client.call_tool(name, inputs)
        report["calls"].append(
            {
                "tool": name,
                "input": inputs,
                "elapsed_seconds": time.monotonic() - started,
                "is_error": response.is_error,
                "structured_content": response.structured_content,
                "content": [item.model_dump(mode="json") for item in response.content]
                if response.is_error
                else None,
            }
        )
        if expect_error:
            assert response.is_error, response
            return response
        assert not response.is_error, response
        return response.structured_content

    async def job(client, name, inputs):
        queued = await call(client, name, inputs)
        report["jobs"].append(
            {"tool": name, "input": inputs, "job_id": queued["job_id"], "terminal": None}
        )
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            state = await call(
                client, "creo_get_job", {"job_id": queued["job_id"], "detail": "compact"}
            )
            if state["status"] not in ("queued", "running"):
                report["jobs"][-1]["terminal"] = state
                assert state["status"] == "succeeded", state
                assert state["result"]["saved_file_reloaded_and_verified"] is True
                return state
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Unknown outcome for job {queued['job_id']}; do not resubmit")

    try:
        async with Client(params, read_timeout_seconds=30) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            report["tool_count"] = len(tools)
            axis_schema = tools["creo_axis_pattern"].input_schema["properties"]["axis"]
            report["axis_schema"] = axis_schema
            assert {form["properties"]["kind"]["const"] for form in axis_schema["oneOf"]} == {
                "axis",
                "datum_axis_feature",
                "datum_feature",
            }
            capabilities = await call(client, "creo_capabilities", {})
            report["runtime"] = capabilities["runtime"]
            report["references"] = capabilities["references"]
            assert Path(report["runtime"]["code_root"]) == ROOT
            assert not report["runtime"]["source_changed_since_startup"]
            assert (
                "src/creo_mechdog/references.py"
                in report["runtime"]["source_fingerprints_at_startup"]
            )
            assert (
                capabilities["references"]["by_tool"]["creo_axis_pattern"][
                    "compatibility_normalized_to"
                ]
                == "datum_axis_feature"
            )
            invalid = await call(
                client,
                "creo_axis_pattern",
                {
                    "model_id": "a" * 32,
                    "expected_revision": 0,
                    "label": "bad",
                    "leader": "leader",
                    "axis": {"kind": "datum_plane", "axis": "z"},
                },
                expect_error=True,
            )
            assert "datum_axis_feature" in str(invalid.content)
            # An invalid model ID cannot admit a mutation. Its error must occur after
            # the exact reported axis input has passed transport/schema validation.
            reported = await call(
                client,
                "creo_axis_pattern",
                {
                    "model_id": "invalid_model",
                    "expected_revision": 0,
                    "label": "probe",
                    "leader": "leader",
                    "axis": {"kind": "datum_feature", "label": "t82_da1"},
                },
                expect_error=True,
            )
            assert "Pattern requires an axis reference" not in str(reported.content)
            assert any(
                text in str(reported.content) for text in ("Creo is not ready", "Invalid model_id")
            )
            report["reported_axis_passed_wire_validation"] = True
            report["protocol_verified"] = True
            if args.create:
                status = await call(client, "creo_startup_status", {})
                deadline = time.monotonic() + 130
                retried = False
                while status["state"] != "ready" and time.monotonic() < deadline:
                    if status["state"] not in {
                        "checking",
                        "building_worker",
                        "starting",
                        "waiting_for_connection",
                    }:
                        if args.retry and not retried and status.get("retry_allowed"):
                            status = await call(client, "creo_startup_status", {"retry": True})
                            retried = True
                            continue
                        break
                    await asyncio.sleep(1)
                    status = await call(client, "creo_startup_status", {})
                report["startup"] = status
                if status["state"] != "ready":
                    report["native"] = "unverified_toolkit_not_ready"
                else:
                    report["session"] = await call(client, "creo_session_status", {})
                    assert report["session"]["connected"]
                    initial = await job(
                        client,
                        "creo_execute_plan",
                        {
                            "operations": [
                                {
                                    "op": "datum_axis",
                                    "label": "spin_axis",
                                    "references": [
                                        {"kind": "datum_plane", "axis": "x"},
                                        {"kind": "datum_plane", "axis": "y"},
                                    ],
                                },
                                {
                                    "op": "sketch",
                                    "label": "base_profile",
                                    "entities": [
                                        {
                                            "type": "rectangle",
                                            "name": "base",
                                            "min": [-20, -10],
                                            "max": [20, 10],
                                        }
                                    ],
                                },
                                {
                                    "op": "extrude",
                                    "label": "base",
                                    "sketch": "base_profile",
                                    "depth": 4,
                                },
                                {
                                    "op": "sketch",
                                    "label": "boss_profile",
                                    "offset": 4,
                                    "entities": [
                                        {
                                            "type": "circle",
                                            "name": "boss",
                                            "center": [12, 0],
                                            "radius": 2,
                                        }
                                    ],
                                },
                                {
                                    "op": "extrude",
                                    "label": "boss",
                                    "sketch": "boss_profile",
                                    "depth": 2,
                                },
                            ],
                            "assertions": {"require_solid": True, "volume_mm3": 3200 + 8 * math.pi},
                        },
                    )
                    patterned = await job(
                        client,
                        "creo_axis_pattern",
                        {
                            "model_id": initial["model_id"],
                            "expected_revision": initial["revision"],
                            "label": "two_bosses",
                            "leader": "boss",
                            "axis": {"kind": "datum_feature", "label": "spin_axis"},
                            "count": 2,
                            "increment_deg": 180,
                        },
                    )
                    inspection = patterned["result"]["inspection"]
                    assert abs(inspection["volume_mm3"] - (3200 + 16 * math.pi)) < 0.01
                    assert patterned["revision"] == initial["revision"] + 1
                    report["native"] = "passed"
            report["success"] = report["protocol_verified"] and (
                not args.create or report["native"] == "passed"
            )
    except Exception as exc:
        report["failure"] = str(exc)
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                key: report.get(key)
                for key in ("success", "protocol_verified", "tool_count", "native", "failure")
            }
        )
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true")
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Explicitly recheck a terminal startup failure; may launch configured Creo, never closes a session",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "build/bug006-mcp.json")
    args = parser.parse_args()
    return 0 if asyncio.run(run(args))["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

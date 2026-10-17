"""FEAT-029 developer phase capture via real stdio MCP; never operates GUI or deploys DLLs.

Run once per operator-prepared phase. --previous compares immutable identities and
registration artifacts; it cannot independently prove which GUI actions occurred.
Use test_direct_loft.py --suite --work-item FEAT-029 for modeling after readiness.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from tools.dev_check import git_state, source_hash
from version import VERSION

ROOT = Path(__file__).resolve().parents[1]


async def capture(args: argparse.Namespace) -> dict:
    report = {
        "work_item": "FEAT-029",
        "version": VERSION,
        "phase": args.phase,
        "startup_disabled_for_observation": args.no_startup,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"os": platform.platform(), "python": platform.python_version()},
        "source": {
            **git_state(ROOT),
            "fingerprints": {
                p.relative_to(ROOT).as_posix(): source_hash(p)
                for p in [
                    ROOT / "bridge.py",
                    ROOT / "server.py",
                    *ROOT.glob("native/*callback*.h"),
                    ROOT / "native/blend_loader.cpp",
                    ROOT / "native/blend_sync.cpp",
                    ROOT / "src/creo_mechdog/blend_callback.py",
                ]
            },
        },
        "operator_actions": {
            "registration": args.registration_action,
            "manual_start": args.manual_start,
            "creo_restarts": args.creo_restarts,
            "source": "operator declaration; not inferred from files",
        },
        "calls": [],
        "success": False,
        "unverified": [
            "GUI registration persistence",
            "modeling in this snapshot-only run",
            "WorkBuddy final acceptance",
            "concurrency",
            "Creo 10",
        ],
    }
    try:
        arguments = [str(ROOT / "server.py")]
        if args.no_startup:
            arguments = [
                "-c",
                "import server; server.startup.start=lambda:None; server.updates.start=lambda:None; server.mcp.run()",
            ]
        params = StdioServerParameters(command=sys.executable, args=arguments, cwd=ROOT)
        async with Client(params, read_timeout_seconds=30) as client:
            tools = await client.list_tools()
            report["tool_names"] = [tool.name for tool in tools.tools]
            for name in ("creo_capabilities", "creo_callback_status"):
                response = await client.call_tool(name, {})
                value = response.structured_content
                report["calls"].append(
                    {
                        "tool": name,
                        "input": {},
                        "is_error": response.is_error,
                        "result": value,
                        "raw": [c.model_dump(mode="json") for c in response.content]
                        if response.is_error
                        else [],
                    }
                )
                if response.is_error:
                    raise RuntimeError(f"{name} failed")
                report["capabilities" if name == "creo_capabilities" else "callback"] = value
        callback = report["callback"]
        artifacts = {}
        for key in ("registry_file", "module_file", "loader_file"):
            if callback.get(key) and Path(callback[key]).is_file():
                p = Path(callback[key])
                artifacts[key] = {
                    "path": str(p),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
        report["artifacts"] = artifacts
        if args.previous:
            previous = json.loads(args.previous.read_text(encoding="utf-8"))
            report["comparison"] = {
                "previous_phase": previous["phase"],
                "same_resource_root": previous["callback"].get("resource_root")
                == callback.get("resource_root"),
                "same_registration_artifact": previous.get("artifacts", {}).get("registry_file")
                == artifacts.get("registry_file"),
                "same_loader": previous["callback"].get("loader_sha256")
                == callback.get("loader_sha256"),
                "payload_changed": previous["callback"].get("dll_sha256")
                != callback.get("dll_sha256"),
                "gui_actions_verified": False,
            }
        if args.expect and callback["readiness"] != args.expect:
            raise RuntimeError(f"Expected {args.expect}, observed {callback['readiness']}")
        report["success"] = True
        report["scope"] = (
            "Public interface phase observation only; not full lifecycle/modeling acceptance"
        )
    except Exception as exc:
        report["failure"] = repr(exc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "success": report["success"],
                "readiness": report.get("callback", {}).get("readiness"),
                "failure": report.get("failure"),
            },
            ensure_ascii=False,
        )
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        required=True,
        choices=["baseline", "upgraded", "restarted", "rollback", "coexist", "offline"],
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument(
        "--no-startup",
        action="store_true",
        help="Developer observation server disables background startup/update; public callback tool still probes the actual existing session",
    )
    parser.add_argument("--expect", choices=["ready", "not_loaded", "version_mismatch", "unknown"])
    parser.add_argument(
        "--registration-action",
        choices=["none", "registered", "changed", "unknown"],
        default="unknown",
    )
    parser.add_argument("--manual-start", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--creo-restarts", type=int)
    args = parser.parse_args()
    if args.creo_restarts is not None and args.creo_restarts < 0:
        parser.error("--creo-restarts must be nonnegative")
    return 0 if asyncio.run(capture(args))["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

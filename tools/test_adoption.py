"""FEAT-042 real-machine adoption flow: managed copy of the user's current model.

The script prepares a realistic "user part" outside the managed tree, asks the
operator to open it in Creo (optionally adding one unsaved feature), then drives
the whole contract through the public MCP interface only: inspect identity,
apply a managed copy, prove the source file untouched, edit the copy, and refuse
a repeated adoption. A sheetmetal stage repeats the flow.

Run: .venv\\Scripts\\python.exe tools\\test_adoption.py
The script pauses for manual Creo interaction; keep the Creo session open.
"""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.mcp_readiness import wait_for_startup
from version import VERSION

report = {"version": VERSION, "cases": [], "started_at": time.time()}
USER_DIR = Path(tempfile.gettempdir()) / "feat042_user_parts"


async def call(client, name, args):
    r = await client.call_tool(name, args)
    if r.is_error:
        raise RuntimeError(f"{name}: {r.content}")
    return r.structured_content


async def job(client, name, args, expect_success=True):
    created = await call(client, name, args)
    print(f"{name} job={created['job_id']} model={created.get('model_id')}", flush=True)
    result = created
    for _ in range(330):
        if result.get("status") not in (None, "queued", "running"):
            break
        result = await call(
            client, "creo_get_job", {"job_id": created["job_id"], "detail": "compact"}
        )
        await asyncio.sleep(1)
    report["cases"].append({"tool": name, "args": args, "job": result})
    (ROOT / "build/adoption_integration_test.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"result={result['status']} stage={result.get('stage')} message={result.get('message')}",
        flush=True,
    )
    if expect_success:
        assert result["status"] == "succeeded", str(result.get("message"))
        assert result["result"]["saved_file_reloaded_and_verified"] is True
    return created, result


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


async def seed_part(client, stage: str) -> Path:
    """Build a small managed part, then copy its saved file out as the user file."""
    created, result = await job(
        client,
        "creo_execute_plan",
        {
            "model_name": f"feat042_seed_{stage}",
            "operations": [
                {
                    "op": "sketch",
                    "label": "base_profile",
                    "plane": "XY",
                    "entities": [
                        {
                            "type": "circle",
                            "name": "base_circle",
                            "center": [0, 0],
                            "radius": 12,
                        }
                    ],
                    "dimensions": [
                        {
                            "name": "base_diameter",
                            "type": "diameter",
                            "refs": [{"entity": "base_circle"}],
                            "value": 24,
                        }
                    ],
                },
                {
                    "op": "extrude",
                    "label": "base_pad",
                    "sketch": "base_profile",
                    "depth": 10,
                },
            ],
            "assertions": {"require_solid": True},
        },
    )
    created["model_id"]
    part = Path(result["result"]["part_file"])
    user_file = USER_DIR / f"user_{stage}.prt"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(part, user_file)
    return user_file


async def seed_sheetmetal(client) -> Path:
    created, _ = await job(client, "creo_new_sheetmetal", {"model_name": "feat042_seed_sm"})
    model_id = created["model_id"]
    rev = created["revision"]
    _, result = await job(
        client,
        "creo_execute_plan",
        {
            "model_id": model_id,
            "expected_revision": rev,
            "operations": [
                {
                    "op": "sketch",
                    "label": "wall_profile",
                    "plane": "XY",
                    "entities": [
                        {
                            "type": "polyline",
                            "name": "wall_line",
                            "points": [[0, 0], [30, 0]],
                        }
                    ],
                },
                {
                    "op": "sheetmetal_wall",
                    "label": "first_wall",
                    "sketch": "wall_profile",
                    "depth": 20,
                    "thickness": 2,
                },
            ],
        },
    )
    part = Path(result["result"]["part_file"])
    user_file = USER_DIR / "user_sm.prt"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(part, user_file)
    return user_file


def open_in_creo(user_file: Path) -> None:
    """Windows shell association usually routes the file into the running Creo."""
    try:
        os.startfile(str(user_file))  # noqa: S606 - deliberate user-file association open
    except OSError as error:
        print(f"auto-open via shell association failed ({error}); open it manually", flush=True)


async def wait_until_current(client, user_file: Path, timeout: float = 120.0) -> bool:
    stem = user_file.stem.lower()
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = await call(client, "creo_session_status", {})
        # Creo renders names uppercased and possibly mangled (BUG-070); a
        # lowercase containment check on the readable stem stays robust.
        if stem in (status.get("current_model") or "").lower():
            return True
        await asyncio.sleep(2)
    return False


async def run_stage(client, stage: str, user_file: Path, managed_name: str, *, boss: bool):
    print(f"\n=== stage {stage}: {user_file} ===", flush=True)
    before = digest(user_file)
    open_in_creo(user_file)
    if not await wait_until_current(client, user_file):
        input(
            f"Could not confirm {user_file} as the current model; open it in Creo "
            "and make it the current window model, then press Enter..."
        )
        assert await wait_until_current(client, user_file, timeout=300.0), (
            "the user file never became the current window model"
        )
    evidence = await call(client, "creo_adopt_current_model", {})
    report["cases"].append(
        {"tool": "creo_adopt_current_model#inspect", "stage": stage, "result": evidence}
    )
    assert evidence["available"], str(evidence)
    assert Path(evidence["file"]["path"]).resolve() == user_file.resolve(), evidence["file"]["path"]
    assert evidence["file"]["sha256"] == before, "inspect hash must match the source file"
    live = evidence["current_model"]
    print(
        f"inspect origin={evidence['file']['path']} type={live['model_type']} "
        f"features={live['feature_count']} volume={live['volume_mm3']}",
        flush=True,
    )
    created, result = await job(
        client,
        "creo_adopt_current_model",
        {
            "mode": "apply",
            "model_id": evidence["model_id"],
            "evidence_token": evidence["evidence_token"],
            "model_name": managed_name,
            "idempotency_key": f"feat042_{stage}_apply",
        },
    )
    managed_id = evidence["model_id"]
    after = await call(client, "creo_inspect_model", {"model_id": managed_id})
    assert after["status"] == "ready", after
    assert after["revision"] == 1, after
    assert after["model_name"] == managed_name
    adopted = after.get("adopted_from")
    if adopted:
        assert Path(adopted["origin"]).resolve() == user_file.resolve()
        assert adopted["state"] == "completed"
    else:
        print(
            "note: compact inspect does not expose adopted_from; verified via job/conflict",
            flush=True,
        )
    assert digest(user_file) == before, "the user's source file must stay byte-identical"
    inspection = result["result"]["inspection"]
    copied_features = len(inspection["features"])
    print(
        f"adopted features={copied_features} (inspect saw {live['feature_count']}); "
        "equal => unsaved session state was adopted",
        flush=True,
    )
    report["cases"].append(
        {
            "stage": stage,
            "unsaved_state_adopted": copied_features == live["feature_count"],
            "inspect_features": live["feature_count"],
            "adopted_features": copied_features,
        }
    )
    # The managed copy is fully editable through the ordinary plan path.
    # The managed copy is fully editable through the ordinary plan path.
    if boss:
        operations = [
            {
                "op": "sketch",
                "label": "top_boss",
                "plane": "XY",
                "offset": 10,
                "entities": [
                    {"type": "circle", "name": "boss_circle", "center": [0, 0], "radius": 4}
                ],
            },
            {"op": "extrude", "label": "boss_pad", "sketch": "top_boss", "depth": 5},
        ]
    else:
        # Solid extrusions on a sheetmetal body stay unproven; a parameter edit
        # plus regenerate still proves the full plan/save/reload pipeline.
        operations = [
            {"op": "set_parameters", "values": {"feat042_stage": stage}},
            {"op": "regenerate"},
        ]
    edit, _ = await job(
        client,
        "creo_execute_plan",
        {
            "model_id": managed_id,
            "expected_revision": after["revision"],
            "operations": operations,
        },
    )
    edited = await call(client, "creo_inspect_model", {"model_id": managed_id})
    assert edited["revision"] == after["revision"] + 1, edited
    # A second adoption of the same source is an explicit conflict.
    repeat = await call(client, "creo_adopt_current_model", {})
    report["cases"].append(
        {"tool": "creo_adopt_current_model#repeat", "stage": stage, "result": repeat}
    )
    assert not repeat["available"], repeat
    assert repeat["conflict"]["model_id"] == managed_id, repeat
    print(f"stage {stage}: adoption, edit, save/reload and conflict refusal all OK", flush=True)
    return managed_id


async def run_current_stage(client, managed_name: str):
    """Adopt the current window model, which must be unregistered by the caller."""
    evidence = await call(client, "creo_adopt_current_model", {})
    report["cases"].append(
        {"tool": "creo_adopt_current_model#inspect", "stage": "current", "result": evidence}
    )
    assert evidence["available"], str(evidence)
    origin = Path(evidence["file"]["path"])
    print(f"\n=== stage current: {origin} ===", flush=True)
    before = digest(origin)
    assert evidence["file"]["sha256"] == before
    live = evidence["current_model"]
    print(
        f"inspect origin={origin} type={live['model_type']} "
        f"features={live['feature_count']} volume={live['volume_mm3']}",
        flush=True,
    )
    created, result = await job(
        client,
        "creo_adopt_current_model",
        {
            "mode": "apply",
            "model_id": evidence["model_id"],
            "evidence_token": evidence["evidence_token"],
            "model_name": managed_name,
            "idempotency_key": "feat042_current_apply",
        },
    )
    managed_id = evidence["model_id"]
    after = await call(client, "creo_inspect_model", {"model_id": managed_id})
    assert after["status"] == "ready", after
    assert after["revision"] == 1, after
    assert after["model_name"] == managed_name
    assert digest(origin) == before, "the source file must stay byte-identical"
    copied = result["result"]["inspection"]["counts"]["features"]
    print(
        f"adopted features={copied} (inspect saw {live['feature_count']}); "
        "equal => the session state was copied",
        flush=True,
    )
    report["cases"].append(
        {
            "stage": "current",
            "session_state_copied": copied == live["feature_count"],
            "inspect_features": live["feature_count"],
            "adopted_features": copied,
        }
    )
    # The managed copy is editable through the ordinary plan path.
    await job(
        client,
        "creo_execute_plan",
        {
            "model_id": managed_id,
            "expected_revision": after["revision"],
            "operations": [
                {
                    "op": "sketch",
                    "label": "top_boss",
                    "plane": "XY",
                    "offset": 10,
                    "entities": [
                        {"type": "circle", "name": "boss_circle", "center": [0, 0], "radius": 4}
                    ],
                },
                {"op": "extrude", "label": "boss_pad", "sketch": "top_boss", "depth": 5},
            ],
        },
    )
    edited = await call(client, "creo_inspect_model", {"model_id": managed_id})
    assert edited["revision"] == after["revision"] + 1, edited
    repeat = await call(client, "creo_adopt_current_model", {})
    report["cases"].append(
        {"tool": "creo_adopt_current_model#repeat", "stage": "current", "result": repeat}
    )
    assert not repeat["available"], repeat
    assert repeat["conflict"]["model_id"] == managed_id, repeat
    print("stage current: adoption, edit, save/reload and conflict refusal all OK", flush=True)


async def main():
    parser = argparse.ArgumentParser(description="FEAT-042 adoption integration flow")
    parser.add_argument(
        "--current",
        action="store_true",
        help="adopt the unregistered current window model instead of manual file opening",
    )
    arguments = parser.parse_args()
    async with Client(
        StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT),
        read_timeout_seconds=90,
    ) as client:
        await wait_for_startup(client, report, ROOT / "build/adoption_integration_test.json")
        status = await call(client, "creo_session_status", {})
        assert status["connected"], status
        if arguments.current:
            await run_current_stage(client, "feat042_adopted_run2")
            report["success"] = True
        else:
            part_file = await seed_part(client, "part")
            await run_stage(client, "part", part_file, "feat042_adopted_part", boss=True)
            sheet_file = await seed_sheetmetal(client)
            await run_stage(client, "sheetmetal", sheet_file, "feat042_adopted_sm", boss=False)
            report["success"] = len(report["cases"]) >= 8
    (ROOT / "build/adoption_integration_test.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "ADOPTION_INTEGRATION_SUCCESS" if report["success"] else "ADOPTION_INTEGRATION_INCOMPLETE",
        flush=True,
    )
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

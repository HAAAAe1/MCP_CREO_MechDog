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
import shutil
import sys
import tempfile
import time
import uuid
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


async def session_inventory(client):
    page = await call(client, "creo_list_session_models", {"limit": 50})
    result = {**page, "models": list(page["models"])}
    while page.get("next_cursor"):
        page = await call(
            client, "creo_list_session_models", {"limit": 50, "cursor": page["next_cursor"]}
        )
        assert page["snapshot_id"] == result["snapshot_id"]
        result["models"].extend(page["models"])
    result["next_cursor"] = None
    return result


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
    """Keep the operator in the existing session rather than spawning another Creo."""
    input(
        f"Open {user_file} using File > Open in the existing Creo session, activate it, then press Enter..."
    )


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
    full = await call(client, "creo_get_job", {"job_id": created["job_id"], "detail": "full"})
    inspection = full["result"]["inspection"]
    copied_features = len(inspection["features"])
    assert copied_features == live["feature_count"]
    assert abs(inspection["volume_mm3"] - live["volume_mm3"]) <= 0.01
    print(
        f"adopted features={copied_features} (inspect saw {live['feature_count']}); "
        "native verification compared source/copy/reload geometry and parameters",
        flush=True,
    )
    report["cases"].append(
        {
            "stage": stage,
            "source_copy_reload_verified": full["result"]["saved_file_reloaded_and_verified"],
            "unsaved_modifications_tested": False,
            "inspect_features": live["feature_count"],
            "adopted_features": copied_features,
        }
    )
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


async def run_current_stage(client, managed_name: str, *, require_dirty: bool = False):
    """Adopt the current window model, which must be unregistered by the caller."""
    evidence = await call(client, "creo_adopt_current_model", {})
    if require_dirty:
        listing = await session_inventory(client)
        current = [m for m in listing["models"] if m["is_current"]]
        assert len(current) == 1 and current[0]["modified"] is True, (
            "make an unsaved design change first"
        )
        assert current[0]["has_saved_origin"] is True, (
            "dirty-current requires an existing saved source"
        )
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
    assert copied == live["feature_count"]
    assert abs(result["result"]["inspection"]["volume_mm3"] - live["volume_mm3"]) <= 0.01
    print(
        f"adopted features={copied} (inspect saw {live['feature_count']}); "
        "native source/copy/reload verification passed",
        flush=True,
    )
    report["cases"].append(
        {
            "stage": "current",
            "source_copy_reload_verified": True,
            "unsaved_modifications_tested": require_dirty,
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


async def run_unsaved_box(client, *, change_after_prepare: bool = False):
    """Operator-created never-saved box; no registry removal or fabricated source."""
    inventory = await session_inventory(client)
    current = [m for m in inventory["models"] if m["is_current"]]
    assert len(current) == 1, "the current model must appear in the inventory"
    source = current[0]
    assert source["name"].lower() == "001" and source["has_saved_origin"] is False, source
    preflight = await call(client, "creo_adopt_current_model", {})
    assert preflight["available_modes"] == ["prepare"] and preflight["model_id"] is None
    suffix = uuid.uuid4().hex[:8]
    args = {
        "mode": "prepare",
        "model_name": f"adopt_box_{suffix}",
        "idempotency_key": f"prepare_box_{suffix}",
    }
    prepared, result = await job(client, "creo_adopt_current_model", args)
    assert result["revision"] == 0 and result["stage"] == "snapshot_prepared"
    evidence = result["result"]["adoption"]
    mid = evidence["model_id"]
    state = await call(client, "creo_inspect_model", {"model_id": mid})
    assert state["status"] == "adopt_pending" and state["revision"] == 0
    full = await call(client, "creo_get_job", {"job_id": prepared["job_id"], "detail": "full"})
    captured = full["result"]["inspection"]
    assert abs(captured["volume_mm3"] - 24000) <= 0.01, "expected a 40x30x20 box"
    after_prepare = await session_inventory(client)
    active = [m for m in after_prepare["models"] if m["is_current"]]
    assert len(active) == 1 and active[0]["session_model_id"] == source["session_model_id"]
    assert active[0]["has_saved_origin"] is False
    refused = await client.call_tool(
        "creo_execute_plan",
        {
            "model_id": mid,
            "expected_revision": 0,
            "operations": [{"op": "regenerate"}],
        },
    )
    assert refused.is_error, "unconfirmed snapshot must not permit ordinary modeling"
    if change_after_prepare:
        input(
            "Change dimensions/parameters or close the original 001 in Creo WITHOUT saving; press Enter to confirm the frozen snapshot..."
        )
    renewed = await call(client, "creo_adopt_current_model", {"mode": "inspect", "model_id": mid})
    assert renewed["file"] == evidence["file"], "renewal must retain the same snapshot"
    _, confirmed = await job(
        client,
        "creo_adopt_current_model",
        {
            "mode": "apply",
            "model_id": mid,
            "evidence_token": renewed["evidence_token"],
            "idempotency_key": f"confirm_box_{suffix}",
        },
    )
    assert confirmed["revision"] == 1
    geometry = await call(client, "creo_get_job", {"job_id": confirmed["job_id"], "detail": "full"})
    surfaces = geometry["result"]["inspection"]["surfaces"]
    top = [
        s
        for s in surfaces
        if abs(s.get("origin", [0, 0, -1])[2] - 20) < 0.01
        and abs(s.get("normal", [0, 0, 0])[2]) > 0.99
    ]
    assert len(top) == 1, "expected one planar top face at Z=20"
    _, shell = await job(
        client,
        "creo_execute_plan",
        {
            "model_id": mid,
            "expected_revision": 1,
            "operations": [
                {
                    "op": "shell",
                    "label": "confirmed_shell",
                    "thickness": 2,
                    "remove_surfaces": [{"kind": "surface", "id": top[0]["id"]}],
                }
            ],
            "assertions": {"require_solid": True, "volume_mm3": 7152, "volume_tolerance": 0.01},
        },
    )
    assert shell["revision"] == 2
    assert abs(shell["result"]["inspection"]["volume_mm3"] - 7152) <= 0.01
    replay = await call(client, "creo_adopt_current_model", args)
    assert replay["job_id"] == prepared["job_id"]
    assert (await call(client, "creo_inspect_model", {"model_id": mid}))["revision"] == 2
    final_inventory = await session_inventory(client)
    originals = [
        m for m in final_inventory["models"] if m["session_model_id"] == source["session_model_id"]
    ]
    if not change_after_prepare:
        assert len(originals) == 1 and originals[0]["has_saved_origin"] is False
    report["cases"].append(
        {
            "stage": "never_saved_box",
            "source_before": source,
            "source_after": originals,
            "operator_changed_source": change_after_prepare,
            "frozen_snapshot": evidence["file"],
            "source_inspection": full["result"]["live"]["inspection"],
            "snapshot_inspection": captured,
            "final_volume_mm3": 7152,
            "revisions": [0, 1, 2],
        }
    )


async def main():
    parser = argparse.ArgumentParser(description="FEAT-042 adoption integration flow")
    parser.add_argument(
        "--current",
        action="store_true",
        help="adopt the unregistered current window model instead of manual file opening",
    )
    parser.add_argument(
        "--unsaved-box",
        action="store_true",
        help="manually create 001, 40x30 on XY, Z=0..20, mm, never save, then test prepare/confirm/shell",
    )
    parser.add_argument(
        "--dirty-current",
        action="store_true",
        help="require a saved external source with unsaved design changes",
    )
    parser.add_argument(
        "--change-after-prepare",
        action="store_true",
        help="pause for changing/closing the original after freezing (--unsaved-box)",
    )
    arguments = parser.parse_args()
    if sum((arguments.current, arguments.unsaved_box, arguments.dirty_current)) > 1:
        parser.error("choose only one of --current, --unsaved-box, --dirty-current")
    if arguments.change_after_prepare and not arguments.unsaved_box:
        parser.error("--change-after-prepare requires --unsaved-box")
    async with Client(
        StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT),
        read_timeout_seconds=90,
    ) as client:
        await wait_for_startup(client, report, ROOT / "build/adoption_integration_test.json")
        status = await call(client, "creo_session_status", {})
        assert status["connected"], status
        if arguments.unsaved_box:
            await run_unsaved_box(client, change_after_prepare=arguments.change_after_prepare)
            report["success"] = True
        elif arguments.current or arguments.dirty_current:
            await run_current_stage(
                client,
                f"adopt_current_{uuid.uuid4().hex[:8]}",
                require_dirty=arguments.dirty_current,
            )
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

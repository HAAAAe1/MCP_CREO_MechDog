"""Real stdio P1 reproduction/regression; never retry an uncertain mutation."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and not __package__:
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "tools.test_p1_modeling", *sys.argv[1:]], cwd=ROOT)
    )

from creo_mechdog.model_queries import RESPONSE_BUDGET, serialized_size
from creo_mechdog.query_client import read_full_model
from tools.dev_check import git_state, source_hash
from tools.test_direct_loft import Probe, circle_sections, verify_blend
from version import VERSION


def box() -> list[dict]:
    return [
        {
            "op": "sketch",
            "label": "profile",
            "plane": "XY",
            "entities": [{"type": "rectangle", "name": "outline", "min": [0, 0], "max": [60, 40]}],
        },
        {"op": "extrude", "label": "base", "sketch": "profile", "depth": 10},
    ]


def identity(job: dict) -> dict:
    return {"model_id": job["model_id"], "expected_revision": job["revision"]}


def depth(job: dict, label: str = "base") -> dict:
    native = job["result"]["aliases"][label]["feature_id"]
    feature = next(f for f in job["result"]["inspection"]["features"] if f["id"] == native)
    return next(d for d in feature["dimensions"] if abs(d["value"] - 10) < 1e-6)


def edit_volume(height: float, blend: bool) -> float:
    if not blend:
        return 2400 * height
    overlap = max(0, height - 10)
    return (
        2400 * height
        + 4900 * math.pi / 3
        - math.pi * (100 * overlap - 1.6 * overlap**2 + 0.0256 * overlap**3 / 3)
    )


async def verify_rollback(p: Probe, before: dict, failed: dict, digest: str) -> None:
    assert failed["status"] == "failed" and failed["result"]["rollback_succeeded"], failed
    restored = failed["result"]["inspection"]
    assert restored["inspection_source"] == "rollback_verified"
    assert abs(restored["volume_mm3"] - before["result"]["inspection"]["volume_mm3"]) < 0.01
    assert hashlib.sha256(Path(before["result"]["part_file"]).read_bytes()).hexdigest() == digest
    live = await p.job(
        "creo_refresh_model", {"model_id": before["model_id"]}, "live_rollback_check"
    )
    assert live["revision"] == before["revision"]
    assert abs(live["result"]["inspection"]["volume_mm3"] - restored["volume_mm3"]) < 0.01
    assert [f["id"] for f in live["result"]["inspection"]["features"]] == [
        f["id"] for f in before["result"]["inspection"]["features"]
    ]


async def dimensions(p: Probe, args: argparse.Namespace) -> None:
    for blend in (False,) if args.simple_only else (False, True):
        base = await p.job("creo_execute_plan", {"operations": box()}, f"edit_base_{blend}")
        if blend:
            sections = circle_sections()
            for section in sections:
                section["offset"] += 10
                section["entities"][0]["center"] = [30, 20]
            base = await p.job(
                "creo_execute_plan",
                {
                    **identity(base),
                    "operations": sections
                    + [{"op": "loft", "label": "blend_probe", "sections": ["sk_a", "sk_b"]}],
                },
                "edit_blend",
            )
        dim = depth(base)
        edited = await p.job(
            "creo_set_dimensions",
            {**identity(base), "values": [{"id": dim["id"], "value": 12}]},
            f"dimension_{blend}",
            allow_failure=args.reproduce,
        )
        if edited["status"] == "succeeded":
            assert edited["revision"] == base["revision"] + 1
            assert abs(edited["result"]["inspection"]["volume_mm3"] - edit_volume(12, blend)) < 0.01
            base = edited
        relation = await p.job(
            "creo_execute_plan",
            {
                **identity(base),
                "operations": [
                    {"op": "set_parameters", "values": {"SIZE": 14.0}},
                    {"op": "set_relations", "lines": [dim["symbol"] + " = SIZE"]},
                ],
            },
            f"relation_{blend}",
            allow_failure=args.reproduce,
        )
        if relation["status"] == "succeeded":
            assert relation["revision"] == base["revision"] + 1
            assert (
                abs(relation["result"]["inspection"]["volume_mm3"] - edit_volume(14, blend)) < 0.01
            )
            propagated = await p.job(
                "creo_set_parameters",
                {**identity(relation), "values": {"SIZE": 15.0}},
                f"parameter_propagation_{blend}",
            )
            assert (
                abs(propagated["result"]["inspection"]["volume_mm3"] - edit_volume(15, blend))
                < 0.01
            )
            digest = hashlib.sha256(
                Path(propagated["result"]["part_file"]).read_bytes()
            ).hexdigest()
            failed = await p.job(
                "creo_set_dimensions",
                {**identity(propagated), "values": [{"id": dim["id"], "value": 16}]},
                f"relation_controlled_{blend}",
                expected_failure=True,
            )
            if not args.reproduce:
                assert "controlled by relations" in failed["message"], failed
                await verify_rollback(p, propagated, failed, digest)
                after = await p.job(
                    "creo_set_parameters",
                    {**identity(propagated), "values": {"SIZE": 16.0}},
                    f"after_failure_edit_{blend}",
                )
                assert (
                    abs(after["result"]["inspection"]["volume_mm3"] - edit_volume(16, blend)) < 0.01
                )


async def holes(p: Probe, args: argparse.Namespace) -> None:
    for blind in (False, True):
        base = await p.job("creo_execute_plan", {"operations": box()}, f"hole_base_{blind}")
        op = {
            "op": "hole",
            "label": "hole",
            "diameter": 8,
            "placement": {"kind": "plane", "axis": "z", "offset": 10},
            "reference1": {"kind": "datum_plane", "axis": "x"},
            "reference2": {"kind": "datum_plane", "axis": "y"},
            "offset1": 30,
            "offset2": 20,
        }
        if blind:
            op["depth"] = 5
        result = await p.job(
            "creo_execute_plan",
            {
                **identity(base),
                "operations": [op],
                "assertions": {
                    "require_solid": True,
                    "volume_mm3": 24000 - math.pi * 16 * (5 if blind else 10),
                },
            },
            f"hole_{blind}",
            allow_failure=args.reproduce,
        )
        if result["status"] == "failed":
            assert result["result"]["rollback_succeeded"], result


async def ribs(p: Probe, args: argparse.Namespace) -> None:
    for flip, side in (
        (False, "symmetric"),
        (True, "symmetric"),
        (False, "positive"),
        (False, "negative"),
    ):
        operations = box()
        operations[1]["depth"] = 15
        operations += [
            {
                "op": "sketch",
                "label": "wall_profile",
                "plane": "XZ",
                "entities": [
                    {"type": "rectangle", "name": "wall", "min": [0, 15], "max": [60, 45]}
                ],
            },
            {
                "op": "extrude",
                "label": "wall",
                "sketch": "wall_profile",
                "depth": 10,
                "direction": "negative",
            },
            {
                "op": "sketch",
                "label": "rib_profile",
                "plane": "YZ",
                "offset": 30,
                "entities": [
                    {
                        "type": "line",
                        "name": "diagonal",
                        "start": [40, 10] if flip else [10, 40],
                        "end": [10, 40] if flip else [40, 10],
                    }
                ],
            },
        ]
        base = await p.job(
            "creo_execute_plan", {"operations": operations}, f"rib_base_{flip}_{side}"
        )
        result = await p.job(
            "creo_rib",
            {
                **identity(base),
                "label": "rib",
                "sketch": "rib_profile",
                "thickness": 4,
                "side": side,
                "flip": flip,
            },
            f"rib_{flip}_{side}",
            allow_failure=args.reproduce,
        )
        if result["status"] == "succeeded":
            assert abs(result["result"]["inspection"]["volume_mm3"] - 55250) < 0.01
            fid = result["result"]["aliases"]["rib"]["feature_id"]
            feature = next(f for f in result["result"]["inspection"]["features"] if f["id"] == fid)
            assert feature["type"] == 920 and feature["status"] == 0


async def references(p: Probe, args: argparse.Namespace) -> None:
    for kind in ("integer", "numeric_string", "labels", "mixed"):
        base = await p.job(
            "creo_execute_plan", {"operations": circle_sections()}, f"refs_base_{kind}"
        )
        aliases = base["result"]["aliases"]
        ids = [aliases[name]["feature_id"] for name in ("sk_a", "sk_b")]
        sections = {
            "integer": ids,
            "numeric_string": list(map(str, ids)),
            "labels": ["sk_a", "sk_b"],
            "mixed": [ids[0], "sk_b"],
        }[kind]
        result = await p.job(
            "creo_loft",
            {
                **identity(base),
                "label": "blend_probe",
                "sections": sections,
            },
            f"refs_{kind}",
            allow_failure=args.reproduce,
        )
        if result["status"] == "succeeded":
            verify_blend(result, 2, "straight", base, 4900 * math.pi / 3)


async def queries(p: Probe, args: argparse.Namespace) -> None:
    page = await p.call("creo_list_models", {"limit": 5})
    assert page["detail"] == "compact"
    assert serialized_size(page) <= RESPONSE_BUDGET
    for summary in page["models"][:3]:
        mid = summary["model_id"]
        direct = await p.client.call_tool("creo_inspect_model", {"model_id": mid})
        assert not direct.is_error and direct.structured_content["detail"] == "compact"
        p.report["calls"].append(
            {
                "tool": "creo_inspect_model",
                "input": {"model_id": mid},
                "result": direct.structured_content,
                "is_error": False,
            }
        )
        p.save()
        compact = await p.call("creo_inspect_model", {"model_id": mid, "detail": "compact"})
        assert compact["detail"] == "compact"
        assert serialized_size(compact) <= RESPONSE_BUDGET
        whole = await read_full_model(p.call, mid)
        assert whole["revision"] == compact["revision"]
        for key, count in compact["inspection"]["counts"].items():
            if count is not None:
                assert len(whole["inspection"][key]) == count, (mid, key)


async def pattern_edit(p: Probe, args: argparse.Namespace) -> None:
    base = await p.job("creo_execute_plan", {"operations": box()}, "pattern_base")
    hole = await p.job(
        "creo_hole",
        {
            **identity(base),
            "label": "hole",
            "diameter": 8,
            "placement": {"kind": "plane", "axis": "z", "offset": 10},
            "reference1": {"kind": "datum_plane", "axis": "x"},
            "reference2": {"kind": "datum_plane", "axis": "y"},
            "offset1": 30,
            "offset2": 20,
        },
        "pattern_hole",
    )
    fid = hole["result"]["aliases"]["hole"]["feature_id"]
    native = next(f for f in hole["result"]["inspection"]["features"] if f["id"] == fid)
    dim = next(d for d in native["dimensions"] if abs(d["value"] - 30) < 1e-6)
    patterned = await p.job(
        "creo_dimension_pattern",
        {
            **identity(hole),
            "label": "hole_pattern",
            "feature": "hole",
            "dimension_id": dim["id"],
            "count": 4,
            "increment": 8,
        },
        "pattern_four",
    )
    digest = hashlib.sha256(Path(patterned["result"]["part_file"]).read_bytes()).hexdigest()
    # Reproduce the report's actual hole-position edit, independently of Blend.
    for tool, values in (
        ("creo_set_dimensions", {"values": [{"id": dim["id"], "value": 40}]}),
        ("creo_set_relations", {"lines": [dim["symbol"].upper() + " = 40"]}),
    ):
        result = await p.job(
            tool, {**identity(patterned), **values}, tool + "_pattern_40", allow_failure=True
        )
        if result["status"] == "failed":
            await verify_rollback(p, patterned, result, digest)
        else:
            # Success is evidence too; preserve the observed outcome and continue
            # from its actual revision, never reuse the old checkpoint revision.
            patterned = result
            digest = hashlib.sha256(Path(result["result"]["part_file"]).read_bytes()).hexdigest()


async def negative_geometry(p: Probe, args: argparse.Namespace) -> None:
    base = await p.job("creo_execute_plan", {"operations": box()}, "negative_geometry_base")
    digest = hashlib.sha256(Path(base["result"]["part_file"]).read_bytes()).hexdigest()
    invalid = await p.job(
        "creo_hole",
        {
            **identity(base),
            "label": "bad_hole",
            "diameter": 8,
            "placement": {"kind": "plane", "axis": "z", "offset": 10},
            "reference1": {"kind": "datum_plane", "axis": "x"},
            "reference2": {"kind": "datum_plane", "axis": "z"},
            "offset1": 30,
            "offset2": 20,
        },
        "hole_parallel_reference",
        expected_failure=True,
    )
    assert "parallel to placement" in invalid["message"], invalid
    await verify_rollback(p, base, invalid, digest)
    closed = await p.job(
        "creo_rib",
        {
            **identity(base),
            "label": "closed_rib",
            "sketch": "profile",
            "thickness": 4,
        },
        "closed_rib",
        expected_failure=True,
    )
    assert "open profile" in closed["message"], closed
    await verify_rollback(p, base, closed, digest)


async def hole_edges_and_zero(p: Probe, args: argparse.Namespace) -> None:
    for kind in ("edge", "zero"):
        operations = box()
        if kind == "zero":
            operations[0]["entities"][0].update(min=[-30, -20], max=[30, 20])
        base = await p.job(
            "creo_execute_plan", {"operations": operations}, "hole_extra_base_" + kind
        )
        reference1 = {"kind": "datum_plane", "axis": "x"}
        reference2 = {"kind": "datum_plane", "axis": "y"}
        if kind == "edge":
            selected = []
            for axis in (0, 1):
                selected.append(
                    next(
                        e["id"]
                        for e in base["result"]["inspection"]["edges"]
                        if "start" in e
                        and "end" in e
                        and abs(e["start"][axis]) < 1e-6
                        and abs(e["end"][axis]) < 1e-6
                        and abs(e["start"][2] - 10) < 1e-6
                        and abs(e["end"][2] - 10) < 1e-6
                    )
                )
            reference1, reference2 = [{"kind": "edge", "id": i} for i in selected]
        hole = await p.job(
            "creo_hole",
            {
                **identity(base),
                "label": "hole",
                "diameter": 8,
                "placement": {"kind": "plane", "axis": "z", "offset": 10},
                "reference1": reference1,
                "reference2": reference2,
                "offset1": 30 if kind == "edge" else 0,
                "offset2": 20 if kind == "edge" else 0,
            },
            "hole_extra_" + kind,
        )
        assert abs(hole["result"]["inspection"]["volume_mm3"] - (24000 - 160 * math.pi)) < 0.01


async def inspection_and_plan_ids(p: Probe, args: argparse.Namespace) -> None:
    empty = await p.job("creo_new_part", {}, "empty_part")
    assert empty["result"]["inspection"]["has_solid"] is False
    plate = await p.job(
        "creo_create_plate",
        {
            "length": 80,
            "width": 60,
            "thickness": 20,
            "corner_radius": 5,
            "holes": [
                {"x": -30, "y": -20, "diameter": 8},
                {"x": 30, "y": 20, "diameter": 8},
                {"x": 0, "y": 0, "diameter": 10},
            ],
        },
        "verified_plate_counts",
    )
    compact = await p.call("creo_get_job", {"job_id": plate["job_id"], "detail": "compact"})
    state = compact["result"]["inspection"]
    assert state["verified_feature_counts"] == {"extrude": 1, "round": 1, "hole": 3}
    assert state["counts"]["features"] is None and state["counts"]["edges"] is None
    assert state["counts"]["bodies"] == 1
    expected = ((80 * 60 - (4 - math.pi) * 25) - math.pi * (16 + 16 + 25)) * 20
    assert abs(state["volume_mm3"] - expected) < 0.01
    base = await p.job("creo_execute_plan", {"operations": circle_sections()}, "plan_id_checkpoint")
    ids = [base["result"]["aliases"][name]["feature_id"] for name in ("sk_a", "sk_b")]
    result = await p.job(
        "creo_execute_plan",
        {
            **identity(base),
            "operations": [
                {"op": "loft", "label": "blend_probe", "sections": [str(ids[0]), ids[1]]}
            ],
        },
        "plan_numeric_ids",
    )
    verify_blend(result, 2, "straight", base, 4900 * math.pi / 3)


async def unavailable_and_nonintersecting(p: Probe, args: argparse.Namespace) -> None:
    failed_new = await p.job(
        "creo_execute_plan",
        {
            "operations": box(),
            "assertions": {"volume_mm3": 1},
        },
        "new_failure_no_checkpoint",
        expected_failure=True,
    )
    assert failed_new["result"]["inspection"] is None
    compact = await p.call("creo_get_job", {"job_id": failed_new["job_id"], "detail": "compact"})
    assert compact["result"]["inspection"]["inspection_available"] is False
    assert all(value is None for value in compact["result"]["inspection"]["counts"].values())
    base = await p.job(
        "creo_execute_plan",
        {
            "operations": box()
            + [
                {
                    "op": "sketch",
                    "label": "outside",
                    "plane": "YZ",
                    "offset": 100,
                    "entities": [
                        {"type": "line", "name": "line", "start": [10, 40], "end": [40, 10]}
                    ],
                }
            ]
        },
        "outside_rib_profile",
    )
    digest = hashlib.sha256(Path(base["result"]["part_file"]).read_bytes()).hexdigest()
    failed = await p.job(
        "creo_rib",
        {
            **identity(base),
            "label": "outside_rib",
            "sketch": "outside",
            "thickness": 4,
        },
        "nonintersecting_rib",
        expected_failure=True,
    )
    await verify_rollback(p, base, failed, digest)


async def run(args: argparse.Namespace) -> dict:
    sources = [
        *ROOT.glob("*.py"),
        *ROOT.glob("src/**/*.py"),
        *ROOT.glob("native/*.cpp"),
        Path(__file__),
    ]
    report = {
        "work_items": ["BUG-028", "BUG-021", "BUG-014", "BUG-022", "BUG-017", "BUG-013"],
        "version": VERSION,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            **git_state(ROOT),
            "fingerprints": {p.relative_to(ROOT).as_posix(): source_hash(p) for p in sources},
        },
        "python": platform.python_version(),
        "windows": platform.platform(),
        "reproduction_only": args.reproduce,
        "calls": [],
        "jobs": [],
        "success": False,
    }
    p = None
    try:
        async with Client(
            StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT),
            read_timeout_seconds=65,
        ) as client:
            p = Probe(client, report, args.output, 120)
            if args.retry:
                await p.call("creo_startup_status", {"retry": True})
            if args.cases != "queries":
                deadline = time.monotonic() + 120
                while True:
                    startup = await p.call("creo_startup_status", {})
                    if startup["state"] == "ready":
                        break
                    assert (
                        startup["state"]
                        in {"checking", "building_worker", "starting", "waiting_for_connection"}
                        and time.monotonic() < deadline
                    ), startup
                    await asyncio.sleep(1)
            report["session"] = await p.call("creo_session_status", {})
            if args.cases != "queries":
                assert report["session"]["connected"], report["session"]
            for name in args.cases.split(","):
                await {
                    "dimensions": dimensions,
                    "holes": holes,
                    "ribs": ribs,
                    "references": references,
                    "queries": queries,
                    "pattern": pattern_edit,
                    "negative_geometry": negative_geometry,
                    "hole_edges_and_zero": hole_edges_and_zero,
                    "inspection_and_plan_ids": inspection_and_plan_ids,
                    "unavailable_and_nonintersecting": unavailable_and_nonintersecting,
                }[name](p, args)
            report["success"] = True
    except Exception as exc:
        report["failure"] = repr(exc)
        report["writes_stopped_for_uncertain_outcome"] = bool(p and p.uncertain)
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        default="dimensions,holes,hole_edges_and_zero,ribs,references,inspection_and_plan_ids,negative_geometry,unavailable_and_nonintersecting,queries",
    )
    parser.add_argument("--reproduce", action="store_true")
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--simple-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build/p1_modeling.json")
    options = parser.parse_args()
    raise SystemExit(0 if asyncio.run(run(options))["success"] else 1)

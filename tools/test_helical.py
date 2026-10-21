"""FEAT-999 probe: does the equation helix land on the model Z axis, and how does
Creo orient the generated sweep frame at the helix start?

Run with the repository venv from the repository root:
    .\\.venv\\Scripts\\python.exe tools\\test_helical.py

This is a probe, not the acceptance test: it records raw geometry so the thread
profile can be written against the real local frame instead of a guess.
"""
import asyncio
import json
import math
import sys
import time
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import VERSION

report = {"version": VERSION, "cases": [], "started_at": time.time()}


async def call(client, name, args):
    r = await client.call_tool(name, args)
    if r.is_error:
        raise RuntimeError(f"{name}: {r.content}")
    return r.structured_content


async def job(client, name, args, expect_success=True):
    created = await call(client, name, args)
    print(f"{name} job={created['job_id']} model={created.get('model_id')}", flush=True)
    result = None
    for _ in range(330):
        result = await call(client, "creo_get_job", {"job_id": created["job_id"]})
        if result["status"] not in ("queued", "running"):
            break
        await asyncio.sleep(1)
    report["cases"].append({"tool": name, "args": args, "job": result})
    (ROOT / "build" / "helical_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    stage = result.get("stage")
    message = result.get("message")
    print(f"  result={result['status']} stage={stage} message={message}", flush=True)
    if expect_success:
        assert result["status"] == "succeeded", str((message, result.get("job_id")))
    return result


def solid_body(result):
    """The body the new feature wrote geometry into (the default body can stay empty)."""
    bodies = result["result"]["inspection"]["bodies"]
    filled = [b for b in bodies if b.get("has_geometry")]
    assert filled, json.dumps(bodies)
    return filled[0]


def bbox(result):
    return solid_body(result)["bbox"]


def volume(result):
    return result["result"]["inspection"]["volume_mm3"]


def coil_volume(radius, pitch, length, wire):
    """Exact length of a helix times the tube cross-section."""
    turns = length / pitch
    path = turns * math.sqrt((2 * math.pi * radius) ** 2 + pitch**2)
    return path * math.pi * wire * wire


async def main():
    params = StdioServerParameters(
        command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT
    )
    async with Client(params, read_timeout_seconds=120) as client:
        tools = await client.list_tools()
        report["tools"] = sorted(t.name for t in tools.tools)
        print("tools=" + str(len(report["tools"])), flush=True)
        status = await call(client, "creo_session_status", {})
        waited = 0
        while not status["connected"] and waited < 240:
            print(f"  waiting for channel: {status.get('state')} - {status.get('message')}")
            await asyncio.sleep(10)
            waited += 10
            status = await call(client, "creo_session_status", {})
        print("creo_connected=" + str(status["connected"]), flush=True)
        report["session"] = status
        assert status["connected"], status

        run = time.strftime("%H%M%S")

        # --- Case A: equation helix alone -------------------------------------
        a = await job(client, "creo_new_part", {"model_name": f"t_curve_{run}"})
        a = await job(
            client,
            "creo_equation_curve",
            {
                "model_id": a["model_id"],
                "expected_revision": a["revision"],
                "label": "helix_ref",
                "equations": "r = 1.555\ntheta = 360*t*8.333333\nz = 2.1+5*t",
                "system": "cylindrical",
                "param_min": 0.0,
                "param_max": 1.0,
            },
        )
        types = [f["type"] for f in a["result"]["inspection"]["features"]]
        report["case_a_feature_types"] = types
        assert 949 in types, f"PRO_FEAT_CURVE missing from {types}"
        print("  A feature_types=%s" % types, flush=True)

        # --- Case B: circle profile -> pipeline, helix axis, analytic volume ---
        b = await job(client, "creo_new_part", {"model_name": f"t_circle_{run}"})
        b = await job(
            client,
            "creo_helical_sweep",
            {
                "model_id": b["model_id"],
                "expected_revision": b["revision"],
                "label": "coil_circle",
                "radius": 2.0,
                "pitch": 1.0,
                "length": 2.0,
                "start_z": 2.0,
                "mode": "add",
                "profile": [
                    {"type": "circle", "name": "wire", "center": [0, 0], "radius": 0.2}
                ],
            },
        )
        report["case_b_bbox"] = bbox(b)
        report["case_b_volume"] = volume(b)
        expected = coil_volume(2.0, 1.0, 2.0, 0.2)
        report["case_b_volume_expected"] = expected
        print(
            "  B bbox=%s volume=%.6f expected=%.6f" % (json.dumps(bbox(b)), volume(b), expected),
            flush=True,
        )
        assert abs(volume(b) - expected) / expected < 0.01, (volume(b), expected)
        lo, hi = bbox(b)
        assert abs(max(abs(lo[0]), abs(hi[0])) - 2.2) < 0.1, lo
        assert abs(lo[2] - 1.8) < 0.1 and abs(hi[2] - 4.2) < 0.15, hi

        # --- Case C: rectangle probe -> which local axis is radial vs axial ----
        c = await job(client, "creo_new_part", {"model_name": f"t_rect_{run}"})
        c = await job(
            client,
            "creo_helical_sweep",
            {
                "model_id": c["model_id"],
                "expected_revision": c["revision"],
                "label": "coil_rect",
                "radius": 2.0,
                "pitch": 1.0,
                "length": 2.0,
                "start_z": 2.0,
                "mode": "add",
                "profile": [
                    {"type": "rectangle", "name": "band", "min": [-1.0, 0.0], "max": [1.0, 0.5]}
                ],
            },
        )
        report["case_c_bbox"] = bbox(c)
        report["case_c_volume"] = volume(c)
        print("  C bbox=%s volume=%s" % (json.dumps(bbox(c)), volume(c)), flush=True)

        report["finished_at"] = time.time()
        (ROOT / "build" / "helical_probe.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("probe complete", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

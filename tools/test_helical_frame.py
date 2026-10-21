"""FEAT-999 frame probe: locate the local section axes of a helical sweep.

Three small marker circles are placed at a known local offset from the section
origin; the bounding box of each coil then identifies which local axis maps to the
radial direction and which to the axial direction, and with which sign.

    .\\.venv\\Scripts\\python.exe tools\\test_helical_frame.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RADIUS, PITCH, LENGTH, START_Z = 2.0, 1.0, 2.0, 2.0
MARK = 0.1

report = {"started_at": time.time(), "markers": {}}


async def call(client, name, args):
    r = await client.call_tool(name, args)
    if r.is_error:
        raise RuntimeError(f"{name}: {r.content}")
    return r.structured_content


async def job(client, name, args):
    created = await call(client, name, args)
    result = None
    for _ in range(330):
        result = await call(client, "creo_get_job", {"job_id": created["job_id"]})
        if result["status"] not in ("queued", "running"):
            break
        await asyncio.sleep(1)
    assert result["status"] == "succeeded", (name, result.get("message"), created["job_id"])
    return result


def filled_bbox(result):
    bodies = result["result"]["inspection"]["bodies"]
    filled = [b for b in bodies if b.get("has_geometry")]
    assert filled, json.dumps(bodies)
    return filled[0]["bbox"]


async def marker(client, tag, u0, v0, run):
    part = await job(client, "creo_new_part", {"model_name": f"t_ck{tag}_{run}"})
    result = await job(
        client,
        "creo_helical_sweep",
        {
            "model_id": part["model_id"],
            "expected_revision": part["revision"],
            "label": f"mk{tag}",
            "radius": RADIUS,
            "pitch": PITCH,
            "length": LENGTH,
            "start_z": START_Z,
            "mode": "add",
            "frame_normal": "pivot",
            "frame_orient": "constant",
            "frame_pivot_direction": {"kind": "datum_plane", "axis": "z"},
            "profile": [
                {
                    "type": "circle",
                    "name": f"mk{tag}",
                    "center": [u0, v0],
                    "radius": MARK,
                }
            ],
        },
    )
    bb = filled_bbox(result)
    report["markers"][tag] = {
        "local": [u0, v0],
        "bbox": bb,
        "volume": result["result"]["inspection"]["volume_mm3"],
    }
    lo, hi = bb
    print(
        "marker %-4s local=(%+.2f,%+.2f)  radius=[%.3f, %.3f]  z=[%.3f, %.3f]  vol=%.6f"
        % (
            tag,
            u0,
            v0,
            min(abs(lo[0]), abs(lo[1]), abs(hi[0]), abs(hi[1])),
            max(abs(hi[0]), abs(hi[1])),
            lo[2],
            hi[2],
            result["result"]["inspection"]["volume_mm3"],
        ),
        flush=True,
    )
    return bb


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    async with Client(params, read_timeout_seconds=120) as client:
        status = await call(client, "creo_session_status", {})
        waited = 0
        while not status["connected"] and waited < 240:
            print(f"  waiting for channel: {status.get('state')}")
            await asyncio.sleep(10)
            waited += 10
            status = await call(client, "creo_session_status", {})
        assert status["connected"], status
        run = time.strftime("%H%M%S")
        print(
            "helix r=%.2f pitch=%.2f length=%.2f start_z=%.2f; marker circle radius %.2f"
            % (RADIUS, PITCH, LENGTH, START_Z, MARK)
        )
        await marker(client, "org", 0.0, 0.0, run)
        await marker(client, "pu", 1.0, 0.0, run)
        await marker(client, "nu", -1.0, 0.0, run)
        await marker(client, "pv", 0.0, 1.0, run)
        report["finished_at"] = time.time()
        (ROOT / "build" / "helical_frame.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("frame probe complete", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

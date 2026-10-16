"""FEAT-032 acceptance: a true helical M3.5x0.6x5 hex screw thread.

Builds the screw (shank + hex head) and cuts the thread groove as a single
helical sweep whose section plane is normal to the projection of the helix on
the XY plane (frame_normal="pivot" + frame_orient="constant"), i.e. the screw
motion that makes the drawn axial profile the exact thread form.

The removed volume is cross-checked against a numeric integration of the screw
motion: V_removed = (1/c) * integral F(z) dz with c = pitch/2pi and F the
profile-blank overlap moment. Then save/reload and STEP/JPEG export.

    .\\.venv\\Scripts\\python.exe tools\\test_helical_thread.py
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import numpy as np
from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# --- thread geometry (ISO metric M3.5x0.6 external, simplified form) ---
MAJOR_D = 3.5
PITCH = 0.6
R_CREST = MAJOR_D / 2                       # 1.75
D_PITCH = MAJOR_D - 0.6495 * PITCH          # 3.1103
R_C = D_PITCH / 2                           # 1.55515 helix / trajectory radius
THREAD_DEPTH = 0.6134 * PITCH               # 0.36804
R_ROOT = R_CREST - THREAD_DEPTH             # 1.38196
CREST_FLAT = PITCH / 8                      # 0.075
U_CREST = R_CREST - R_C                     # 0.19485
U_ROOT = R_ROOT - R_C                       # -0.17319
HW_CREST = (PITCH - CREST_FLAT) / 2         # 0.2625
TAN30 = np.tan(np.pi / 6)
U_TOP = 0.35                                # profile extended above the blank
HW_TOP = HW_CREST + (U_TOP - U_CREST) * TAN30
Z_START, Z_END = -0.75, 5.0                 # helix spans past both shank ends
SHANK_LEN, HEAD_H, HEAD_AF = 5.0, 2.4, 5.5
HEAD_R = HEAD_AF / np.sqrt(3.0) * 1.0 / np.cos(np.pi / 6) ** 0  # placeholder
HEAD_R = HEAD_AF / 2 / np.cos(np.pi / 6)    # circumradius 3.17543


def profile_points():
    hw_root = HW_CREST - (U_CREST - U_ROOT) * TAN30
    return [
        {"type": "line", "name": "flank1", "start": [U_ROOT, -hw_root], "end": [U_TOP, -HW_TOP]},
        {"type": "line", "name": "top", "start": [U_TOP, -HW_TOP], "end": [U_TOP, HW_TOP]},
        {"type": "line", "name": "flank2", "start": [U_TOP, HW_TOP], "end": [U_ROOT, hw_root]},
        {"type": "line", "name": "root", "start": [U_ROOT, hw_root], "end": [U_ROOT, -hw_root]},
    ]


def expected_volume():
    """Blank volume minus the screw-motion groove removal (numeric integration)."""
    shank = np.pi * R_CREST**2 * SHANK_LEN
    head = 1.5 * np.sqrt(3.0) * HEAD_R**2 * HEAD_H  # hex area = (3*sqrt(3)/2) R^2
    c = PITCH / (2 * np.pi)
    hw = lambda u: HW_CREST + (u - U_CREST) * TAN30  # noqa: E731
    u = np.linspace(U_ROOT, U_TOP, 2000)
    r = R_C + u
    z = np.linspace(Z_START, Z_END, 4000)
    lo_shank = -z[:, None]
    lo_head = 5.0 - z[:, None]
    hw_u = hw(u)[None, :]
    L_shank = np.clip(np.minimum(hw_u, 7.4 - z[:, None]) - np.maximum(-hw_u, lo_shank), 0, None)
    L_head = np.clip(np.minimum(hw_u, 7.4 - z[:, None]) - np.maximum(-hw_u, lo_head), 0, None)
    L = np.where(u[None, :] <= U_CREST, L_shank, L_head)
    F = (r[None, :] * L).sum(axis=1) * (u[1] - u[0])
    removed = F.sum() * (z[1] - z[0]) / c
    return shank + head - removed, shank + head, removed


async def call(client, name, args):
    res = await client.call_tool(name, args)
    if res.is_error:
        raise RuntimeError(f"{name}: {res.content}")
    return res.structured_content


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


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    report = {"started_at": time.time()}
    async with Client(params, read_timeout_seconds=120) as client:
        status = await call(client, "creo_session_status", {})
        waited = 0
        while not status["connected"] and waited < 240:
            print(f"  waiting for channel: {status.get('state')}", flush=True)
            await asyncio.sleep(10)
            waited += 10
            status = await call(client, "creo_session_status", {})
        assert status["connected"], status

        run = time.strftime("%H%M%S")
        part = await job(client, "creo_new_part", {"model_name": f"t_m35_{run}"})
        model_id, revision = part["model_id"], part["revision"]
        report["model_id"] = model_id

        sketch = await job(
            client,
            "creo_create_sketch",
            {
                "model_id": model_id,
                "expected_revision": revision,
                "label": "shank_prof",
                "plane": "XY",
                "entities": [
                    {"type": "circle", "name": "shank", "center": [0, 0], "radius": R_CREST}
                ],
            },
        )
        revision = sketch["revision"]
        ext = await job(
            client,
            "creo_extrude",
            {
                "model_id": model_id,
                "expected_revision": revision,
                "label": "shank",
                "sketch": "shank_prof",
                "depth": SHANK_LEN,
                "mode": "add",
            },
        )
        revision = ext["revision"]

        hex_pts = [
            [HEAD_R * np.cos(np.radians(a)), HEAD_R * np.sin(np.radians(a))]
            for a in range(0, 360, 60)
        ]
        head_entities = [
            {
                "type": "line",
                "name": f"h{i}",
                "start": hex_pts[i],
                "end": hex_pts[(i + 1) % 6],
            }
            for i in range(6)
        ]
        sketch = await job(
            client,
            "creo_create_sketch",
            {
                "model_id": model_id,
                "expected_revision": revision,
                "label": "head_prof",
                "plane": "XY",
                "offset": SHANK_LEN,
                "entities": head_entities,
            },
        )
        revision = sketch["revision"]
        ext = await job(
            client,
            "creo_extrude",
            {
                "model_id": model_id,
                "expected_revision": revision,
                "label": "head",
                "sketch": "head_prof",
                "depth": HEAD_H,
                "mode": "add",
            },
        )
        blank_volume = ext["result"]["inspection"]["volume_mm3"]
        report["blank_volume"] = blank_volume
        revision = ext["revision"]

        cut = await job(
            client,
            "creo_helical_sweep",
            {
                "model_id": model_id,
                "expected_revision": revision,
                "label": "thread",
                "radius": R_C,
                "pitch": PITCH,
                "length": Z_END - Z_START,
                "start_z": Z_START,
                "hand": "right",
                "mode": "cut",
                "frame_normal": "pivot",
                "frame_orient": "constant",
                "frame_pivot_direction": {"kind": "datum_plane", "axis": "z"},
                "profile": profile_points(),
            },
        )
        revision = cut["revision"]
        inspection = cut["result"]["inspection"]
        report["thread_volume"] = inspection["volume_mm3"]
        report["thread_bbox"] = inspection["bodies"]

        expected, blank_analytic, removed = expected_volume()
        report["expected"] = {
            "blank_analytic": blank_analytic,
            "blank_measured": blank_volume,
            "removed_numeric": removed,
            "expected_volume": expected,
            "measured_volume": inspection["volume_mm3"],
            "relative_error": abs(inspection["volume_mm3"] - expected) / expected,
        }

        saved = await job(
            client, "creo_save_model", {"model_id": model_id, "expected_revision": revision}
        )
        report["save"] = {
            key: saved["result"].get(key)
            for key in ("saved_file_reloaded_and_verified", "saved_file", "verified")
            if key in saved["result"]
        }
        report["save_keys"] = list(saved["result"].keys())

        step = await job(client, "creo_export_model", {"model_id": model_id, "format": "step"})
        report["step"] = [op.get("file") for op in step["result"].get("operations", [])]
        jpeg = await job(client, "creo_export_model", {"model_id": model_id, "format": "jpeg"})
        report["jpeg"] = [op.get("file") for op in jpeg["result"].get("operations", [])]

    report["finished_at"] = time.time()
    out = ROOT / "build" / "helical_thread_acceptance.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["expected"], indent=2), flush=True)
    print(f"save: {report['save']}", flush=True)
    print(f"step: {report['step']}\njpeg: {report['jpeg']}", flush=True)
    print("acceptance complete", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

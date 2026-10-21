"""FEAT-999 frame forensics: dump the native element tree of a helical sweep.

The probe sweep is a helix (r=2, pitch=1, length=2, start_z=2) with a circle
section (r=0.1) placed at local (+1, 0). Dumping the extracted element tree shows
what the automatic section frame actually resolved to, which the bounding box
probe could not tell us.

    .\\.venv\\Scripts\\python.exe tools\\probe_sweep_frame.py
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

OUT = ROOT / "build"


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
        part = await job(client, "creo_new_part", {"model_name": f"t_frm_{run}"})
        model_id = part["model_id"]
        result = await job(
            client,
            "creo_helical_sweep",
            {
                "model_id": model_id,
                "expected_revision": part["revision"],
                "label": "probe",
                "radius": 2.0,
                "pitch": 1.0,
                "length": 2.0,
                "start_z": 2.0,
                "mode": "add",
                "profile": [
                    {"type": "circle", "name": "mk", "center": [1.0, 0.0], "radius": 0.1}
                ],
            },
        )
        report["model_id"] = model_id
        report["inspection"] = result["result"]["inspection"]

        for label in ("probe", "probe_helix"):
            dumped = await job(
                client, "creo_dump_feature_tree", {"model_id": model_id, "feature": label}
            )
            files = [op.get("file") for op in dumped["result"].get("operations", [])]
            report.setdefault("trees", {})[label] = files
            print(f"tree {label}: {files}", flush=True)

        shot = await job(client, "creo_export_model", {"model_id": model_id, "format": "jpeg"})
        report["jpeg"] = [op.get("file") for op in shot["result"].get("operations", [])]
        print(f"jpeg: {report['jpeg']}", flush=True)

    report["finished_at"] = time.time()
    OUT.joinpath("sweep_frame_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("probe complete", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

"""BUG-002: real owned-model jobs with concurrent registry polling (Creo required)."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and not __package__:
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "tools.test_registry_native", *sys.argv[1:]], cwd=ROOT
        )
    )

import bridge
import generic_bridge
from tools.dev_check import git_state, source_hash
from version import VERSION


def polled_job(created: dict, report: dict, readers: int) -> dict:
    stop = threading.Event()
    start = threading.Barrier(readers + 1)
    counts = [{"reads": 0, "errors": [], "statuses": set()} for _ in range(readers)]

    def poll(count: dict) -> None:
        start.wait()
        while not stop.is_set():
            try:
                compact = bridge.get_job(created["job_id"], detail="compact")
                full = bridge.get_job(created["job_id"], detail="full")
                bridge.list_jobs(detail="compact")
                bridge.list_jobs(detail="full")
                model = generic_bridge.model_info(created["model_id"])
                generic_bridge.list_models()
                assert compact["job_id"] == full["job_id"] == created["job_id"]
                assert model["model_id"] == created["model_id"]
                assert model["revision"] in (created["revision"], created["revision"] + 1)
                count["reads"] += 1
                count["statuses"].add(full["status"])
            except Exception as exc:
                count["errors"].append(
                    {
                        "type": type(exc).__name__,
                        "winerror": getattr(exc, "winerror", None),
                        "message": str(exc),
                    }
                )
            stop.wait(0.005)

    threads = [threading.Thread(target=poll, args=(count,)) for count in counts]
    for thread in threads:
        thread.start()
    began = time.monotonic()
    try:
        start.wait()
        bridge.run_job(created["job_id"])
    finally:
        stop.set()
        for thread in threads:
            thread.join(timeout=5)
        report["polling"].append(
            {
                "job_id": created["job_id"],
                "elapsed_seconds": time.monotonic() - began,
                "readers": [{**count, "statuses": sorted(count["statuses"])} for count in counts],
            }
        )
    assert all(not thread.is_alive() for thread in threads)
    assert all(count["reads"] > 0 and not count["errors"] for count in counts), counts
    job = bridge.get_job(created["job_id"])
    report["jobs"].append(job)
    print(f"BUG-002 native job {created['job_id']}: {job['status']}", flush=True)
    return job


def queued(operations: list[dict], **kwargs) -> dict:
    # Only suppress detached launch: run the actual current-source worker and
    # registry completion synchronously, within this process's isolated paths.
    with patch.object(generic_bridge.subprocess, "Popen"):
        return generic_bridge.submit(operations, **kwargs)


def verified(job: dict, volume: float, revision: int) -> None:
    assert job["status"] == "succeeded", job.get("message")
    assert job["revision"] == revision
    assert job["result"]["saved_file_reloaded_and_verified"] is True
    inspection = job["result"]["inspection"]
    assert inspection["healthy"] and inspection["has_solid"]
    assert abs(inspection["volume_mm3"] - volume) < 0.001


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readers", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "build/BUG-002-native.json")
    args = parser.parse_args()
    if args.readers < 1:
        parser.error("readers must be positive")
    report = {
        "work_item": "BUG-002",
        "version": VERSION,
        "timestamp_utc": bridge.now(),
        "command": [sys.executable, *sys.argv],
        "source": {
            **git_state(ROOT),
            "fingerprints": {
                name: source_hash(ROOT / name)
                for name in ("bridge.py", "generic_bridge.py", "tools/test_registry_native.py")
            },
        },
        "environment": {"os": platform.platform(), "python": platform.python_version()},
        "jobs": [],
        "polling": [],
        "success": False,
        "scope": "Direct current-source submit/run_job plus real native worker; detached MCP transport requires separate validation",
    }
    try:
        environment = bridge.check_environment()
        report["environment"]["creo_root"] = environment["creo_root"]
        report["environment"]["sdk_ready"] = environment["ready_to_build"]
        report["acceptance_baseline"] = (
            "Creo 10" if "Creo 10." in environment["creo_root"] else "experimental compatibility"
        )
        status = bridge.session_status()
        report["session"] = status
        if not status.get("connected"):
            raise RuntimeError("No connected Creo session; no modeling jobs submitted")
        parent = (ROOT / ".tmp").resolve()
        parent.mkdir(exist_ok=True)
        if not parent.is_relative_to(ROOT):
            raise ValueError("Fixture must be inside the checkout")
        # Preserve models and worker logs for evidence; no automatic native erase.
        fixture = Path(tempfile.mkdtemp(prefix="bug002_native_", dir=parent))
        report["fixture"] = str(fixture)
        with (
            patch.object(bridge, "JOBS", fixture / "jobs"),
            patch.object(generic_bridge, "MODELS", fixture / "models"),
        ):
            created = queued(
                [
                    {
                        "op": "sketch",
                        "label": "profile",
                        "plane": "XY",
                        "entities": [
                            {
                                "type": "rectangle",
                                "name": "outline",
                                "min": [-10, -5],
                                "max": [10, 5],
                            }
                        ],
                    },
                    {"op": "extrude", "label": "solid", "sketch": "profile", "depth": 2},
                ],
                model_name="bug002_" + fixture.name[-8:],
                assertions={"volume_mm3": 400, "require_solid": True},
            )
            first = polled_job(created, report, args.readers)
            verified(first, 400, 1)
            mid = created["model_id"]
            model = generic_bridge.model_info(mid)
            assert model["pending_job"] is None and model["revision"] == 1
            edited = queued(
                [{"op": "set_parameters", "values": {"BUG002_SIZE": 18.0}}],
                model_id=mid,
                expected_revision=1,
                assertions={"volume_mm3": 400, "require_solid": True},
            )
            second = polled_job(edited, report, args.readers)
            verified(second, 400, 2)
            model = generic_bridge.model_info(mid)
            assert model["revision"] == 2 and model["pending_job"] is None
            # Native inspection must contain the parameter, independent of manifest status.
            assert second["result"]["inspection"]["parameters"]["BUG002_SIZE"]["value"] == 18.0
            try:
                queued(
                    [{"op": "set_parameters", "values": {"BUG002_SIZE": 99.0}}],
                    model_id=mid,
                    expected_revision=1,
                )
            except ValueError as exc:
                assert "Stale revision" in str(exc)
                report["stale_revision_rejected"] = True
            else:
                raise AssertionError("Stale revision was accepted")
            before = hashlib.sha256(Path(model["part_file"]).read_bytes()).hexdigest()
            failed = queued(
                [
                    {"op": "set_parameters", "values": {"BUG002_SIZE": 99.0}},
                    {"op": "set_dimensions", "values": [{"id": 2000000000, "value": 12}]},
                ],
                model_id=mid,
                expected_revision=2,
            )
            failure = polled_job(failed, report, args.readers)
            assert failure["status"] == "failed" and failure["result"]["rollback_succeeded"]
            after = generic_bridge.model_info(mid)
            assert (
                after["status"] == "ready"
                and after["revision"] == 2
                and after["pending_job"] is None
            )
            assert hashlib.sha256(Path(model["part_file"]).read_bytes()).hexdigest() == before
            refresh = queued([], model_id=mid, readonly=True)
            fresh = polled_job(refresh, report, args.readers)
            assert fresh["status"] == "succeeded" and fresh["revision"] == 2
            assert fresh["result"]["inspection"]["parameters"] == model["inspection"]["parameters"]
            assert abs(fresh["result"]["inspection"]["volume_mm3"] - 400) < 0.001
            report.update(
                rollback_succeeded=True,
                original_file_unchanged=True,
                revision_correct=True,
                pending_job_cleared=True,
                live_geometry_and_parameters_restored=True,
                success=True,
            )
            report["final_model"] = generic_bridge.model_info(mid)
        report["temporary_files"] = len(list(fixture.rglob("*.tmp")))
        assert report["temporary_files"] == 0
    except Exception as exc:
        report.update(
            success=False,
            error={
                "type": type(exc).__name__,
                "message": str(exc),
                "notes": getattr(exc, "__notes__", []),
            },
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"BUG-002 native validation: success={report['success']}; report={args.output}", flush=True
    )
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

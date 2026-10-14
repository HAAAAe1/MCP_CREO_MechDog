"""BUG-002: isolated Windows registry contention evidence, without Creo."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
# Support the documented file entry point without changing the import search path.
if __name__ == "__main__" and not __package__:
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "tools.test_registry_io", *sys.argv[1:]], cwd=ROOT)
    )

import bridge
from tools.dev_check import git_state, source_hash
from version import VERSION


def payload(sequence: int) -> dict:
    return {"sequence": sequence, "text": "登记完整性", "data": [sequence] * 128}


def check(value: dict) -> None:
    if value != payload(value["sequence"]):
        raise ValueError("Incomplete registry payload")


def error_info(exc: Exception) -> dict:
    return {
        "type": type(exc).__name__,
        "winerror": getattr(exc, "winerror", None),
        "message": str(exc),
    }


def concurrent(path: Path, readers: int, writes: int) -> dict:
    bridge.write_json(path, payload(0))
    stop = threading.Event()
    start = threading.Barrier(readers + 1)
    counts = [{"reads": 0, "errors": []} for _ in range(readers)]

    def reader(count: dict) -> None:
        start.wait()
        while not stop.is_set():
            try:
                check(bridge.read_json(path))
                count["reads"] += 1
            except Exception as exc:
                count["errors"].append(error_info(exc))

    threads = [threading.Thread(target=reader, args=(count,)) for count in counts]
    for thread in threads:
        thread.start()
    errors = []
    succeeded = []
    began = time.monotonic()
    try:
        start.wait()
        for sequence in range(1, writes + 1):
            try:
                bridge.write_json(path, payload(sequence))
                succeeded.append(sequence)
            except Exception as exc:
                errors.append({"sequence": sequence, **error_info(exc)})
    finally:
        stop.set()
        for thread in threads:
            thread.join(timeout=5)
    if any(thread.is_alive() for thread in threads):
        raise RuntimeError("Reader did not stop; fixture must be retained")
    final = bridge.read_json(path)
    check(final)
    return {
        "write_success": len(succeeded),
        "write_errors": errors,
        "read_success": sum(count["reads"] for count in counts),
        "read_errors": [error for count in counts for error in count["errors"]],
        "last_successful_sequence": succeeded[-1] if succeeded else 0,
        "final_sequence": final["sequence"],
        "temporary_files": len(list(path.parent.glob(path.name + ".*.tmp"))),
        "elapsed_seconds": time.monotonic() - began,
    }


def held_handle(path: Path, transient: bool) -> dict:
    """A normal CRT reader deliberately omits FILE_SHARE_DELETE."""
    bridge.write_json(path, payload(0))
    original = path.read_bytes()
    attempted = threading.Event()
    released = threading.Event()
    attempts = []
    replace_owner = bridge if hasattr(bridge, "_atomic_replace") else bridge.os
    replace_name = "_atomic_replace" if hasattr(bridge, "_atomic_replace") else "replace"
    real_replace = getattr(replace_owner, replace_name)
    handle = path.open("rb")

    def replace(source: Path, target: Path) -> None:
        try:
            real_replace(source, target)
            attempts.append({"success": True})
        except OSError as exc:
            attempts.append({"success": False, **error_info(exc)})
            attempted.set()
            raise

    def release() -> None:
        attempted.wait(timeout=5)
        time.sleep(0.2)
        handle.close()
        released.set()

    thread = threading.Thread(target=release) if transient else None
    if thread:
        thread.start()
    began = time.monotonic()
    error = None
    try:
        with patch.object(replace_owner, replace_name, side_effect=replace):
            bridge.write_json(path, payload(1))
    except OSError as exc:
        error = error_info(exc)
    finally:
        if thread:
            thread.join(timeout=6)
        else:
            handle.close()
        if thread and thread.is_alive():
            raise RuntimeError("Holder did not stop")
    elapsed = time.monotonic() - began
    unchanged = path.read_bytes() == original
    temporary_files = len(list(path.parent.glob(path.name + ".*.tmp")))
    final = bridge.read_json(path)
    check(final)
    bridge.write_json(path, payload(2))
    return {
        "transient": transient,
        "conflict_triggered": attempted.is_set(),
        "released": released.is_set(),
        "attempts": attempts,
        "error": error,
        "elapsed_seconds": elapsed,
        "old_bytes_preserved": unchanged,
        "final_sequence": final["sequence"],
        "write_after_release": bridge.read_json(path) == payload(2),
        "temporary_files": temporary_files,
    }


def run_case(root: Path, name: str, args: argparse.Namespace) -> dict:
    directory = root / name.removesuffix(".json")
    directory.mkdir()
    path = directory / name
    bridge.write_json(path, payload(0))
    serial_errors = []
    for sequence in range(1, 101):
        try:
            bridge.write_json(path, payload(sequence))
            if bridge.read_json(path) != payload(sequence):
                raise ValueError("Serial readback mismatch")
        except Exception as exc:
            serial_errors.append(error_info(exc))
    serial = {
        "writes": 100,
        "errors": serial_errors,
        "final_sequence": bridge.read_json(path)["sequence"],
    }
    rounds = []
    for index in range(args.rounds):
        round_root = directory / f"round_{index}"
        round_root.mkdir()
        rounds.append(concurrent(round_root / name, args.readers, args.writes))
    short_root = directory / "short"
    long_root = directory / "long"
    short_root.mkdir()
    long_root.mkdir()
    transient = held_handle(short_root / name, True)
    persistent = held_handle(long_root / name, False)
    return {
        "file": name,
        "serial": serial,
        "rounds": rounds,
        "transient": transient,
        "persistent": persistent,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readers", type=int, default=3)
    parser.add_argument("--writes", type=int, default=400)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--baseline", action="store_true", help="Record pre-fix failures without requiring success"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This probe requires Windows")
    if min(args.readers, args.writes, args.rounds) < 1:
        parser.error("readers, writes and rounds must be positive")
    output = args.output or ROOT / "build/BUG-002-registry-io.json"
    report = {
        "work_item": "BUG-002",
        "version": VERSION,
        "timestamp_utc": bridge.now(),
        "command": [sys.executable, *sys.argv],
        "environment": {"os": platform.platform(), "python": platform.python_version()},
        "source": {
            **git_state(ROOT),
            "bridge_sha256": source_hash(ROOT / "bridge.py"),
            "probe_sha256": source_hash(Path(__file__)),
        },
        "parameters": {"readers": args.readers, "writes": args.writes, "rounds": args.rounds},
        "baseline": args.baseline,
        "retry_budget_seconds": getattr(bridge, "JSON_REPLACE_TIMEOUT", None),
        "success": False,
    }
    fixture_parent = (ROOT / ".tmp").resolve()
    fixture_parent.mkdir(exist_ok=True)
    if not fixture_parent.is_relative_to(ROOT):
        raise ValueError("Fixture path must stay inside the checkout")
    with tempfile.TemporaryDirectory(prefix="bug002_", dir=fixture_parent) as fixture:
        report["cases"] = [
            run_case(Path(fixture), name, args) for name in ("job.json", "model.json")
        ]
        report["temporary_files_before_cleanup"] = len(list(Path(fixture).rglob("*.tmp")))
        report["success"] = all(
            not case["serial"]["errors"]
            and case["serial"]["final_sequence"] == 100
            and all(
                not r["write_errors"]
                and not r["read_errors"]
                and r["read_success"] > 0
                and r["final_sequence"] == args.writes
                and r["temporary_files"] == 0
                for r in case["rounds"]
            )
            and case["transient"]["conflict_triggered"]
            and not case["transient"]["error"]
            and len(case["transient"]["attempts"]) > 1
            and case["transient"]["final_sequence"] == 1
            and case["transient"]["elapsed_seconds"] < 2
            and case["transient"]["temporary_files"] == 0
            and case["persistent"]["conflict_triggered"]
            and case["persistent"]["error"] is not None
            and case["persistent"]["old_bytes_preserved"]
            and case["persistent"]["temporary_files"] == 0
            and case["persistent"]["elapsed_seconds"] < 2
            and case["transient"]["write_after_release"]
            and case["persistent"]["write_after_release"]
            for case in report["cases"]
        )
    report["fixture_removed"] = not Path(fixture).exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"BUG-002 registry probe: success={report['success']}; report={output}", flush=True)
    return 0 if args.baseline or report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

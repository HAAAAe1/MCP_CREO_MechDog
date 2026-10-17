"""Read-only evidence for uncertain jobs; evidence never authorizes replay or unlocking."""

from __future__ import annotations

import ctypes
import hashlib
import json
from ctypes import wintypes
from pathlib import Path


def process_identity(pid: int) -> dict:
    """Use process creation time to distinguish a live runner from a reused PID."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel.OpenProcess
    open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_process.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    times = kernel.GetProcessTimes
    times.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    exit_code = kernel.GetExitCodeProcess
    exit_code.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    handle = open_process(0x1000, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        return {"pid": pid, "alive": False if error == 87 else None, "windows_error": error}
    try:
        created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
        code = wintypes.DWORD()
        if not times(handle, created, exited, system, user) or not exit_code(handle, code):
            return {"pid": pid, "alive": None, "windows_error": ctypes.get_last_error()}
        return {
            "pid": pid,
            "created": (created.dwHighDateTime << 32) | created.dwLowDateTime,
            "alive": code.value == 259,
        }
    finally:
        close(handle)


def file_identity(path: Path) -> dict:
    try:
        size = path.stat().st_size
        if size > 16 * 1024 * 1024:
            return {
                "path": str(path),
                "exists": True,
                "size_bytes": size,
                "sha256": None,
                "hash_not_computed": "File exceeds the 16 MiB diagnostic read budget",
            }
        data = path.read_bytes()
        return {"path": str(path), "exists": True, "sha256": hashlib.sha256(data).hexdigest()}
    except OSError as exc:
        return {
            "path": str(path),
            "exists": None if path.exists() else False,
            "error": type(exc).__name__,
        }


def job_evidence(directory: Path, manifest: dict, model: dict | None = None) -> dict:
    """Do not mutate jobs/models, infer cancellation, or promote a checkpoint to success."""
    result = {
        "job_id": manifest["job_id"],
        "model_id": manifest.get("model_id"),
        "automatic_replay_allowed": False,
        "native_result_present": (directory / "native_result.json").is_file(),
        "next_steps": (
            "Do not resubmit or clear pending_job. Inspect this job's native result/checkpoint, "
            "runner identity and saved file in Creo; preserve the original model/checkpoint. "
            "Use creo_session_status and explicit startup retry to recheck the channel. "
            "A connected channel does not resolve this job or commit its revision. "
            "If the result cannot be verified, operator reconciliation is required."
        ),
    }
    runner = manifest.get("runner_identity")
    if runner:
        current = process_identity(runner["pid"])
        result["runner"] = {
            "recorded": runner,
            "observed": current,
            "same_process": current.get("created") == runner.get("created")
            if current.get("created") and runner.get("created")
            else None,
        }
    else:
        result["runner"] = {"observed": None, "reason": "No recorded process creation identity"}
    checkpoint = directory / "native_checkpoint.json"
    if checkpoint.is_file():
        try:
            data = json.loads(checkpoint.read_text(encoding="utf-8"))
            result["native_checkpoint"] = {
                **file_identity(checkpoint),
                **{
                    key: data[key]
                    for key in (
                        "native_pid",
                        "completion_stage",
                        "delivery_complete",
                        "success",
                        "toolkit_code",
                        "message",
                        "part_file",
                        "saved_file_reloaded_and_verified",
                        "disconnect_code",
                        "disconnect_budget_seconds",
                        "rollback_succeeded",
                    )
                    if key in data
                },
                "authoritative_job_success": False,
            }
        except (OSError, ValueError, TypeError):
            result["native_checkpoint"] = {"readable": False}
    if model:
        resolution = model.get("reconciliation")
        result["resolution"] = resolution
        result["model_currently_available"] = model.get("status") == "ready" and not (
            model.get("pending_job") or model.get("recovery_pending")
        )
        result["model"] = {
            key: model.get(key) for key in ("status", "revision", "pending_job", "last_job")
        }
        if model.get("part_file"):
            result["saved_baseline"] = file_identity(Path(model["part_file"]))
    return result

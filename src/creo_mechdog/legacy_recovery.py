"""Read-only previous-boot evidence for owners predating process identity records."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from creo_mechdog.startup_state import BOOT_FILE_MARGIN_NS


def _signature(path: Path) -> dict:
    if path.is_symlink() or path.is_junction():
        raise ValueError("Historical owner evidence cannot contain links")
    stat = path.stat()
    return {
        "name": path.name,
        "file_id": stat.st_ino,
        "size": stat.st_size,
        "created_ns": getattr(stat, "st_birthtime_ns", stat.st_ctime_ns),
        "modified_ns": stat.st_mtime_ns,
    }


def previous_boot_evidence(directory: Path, job: dict, boot: dict | None) -> dict:
    """Never replace an active/known owner; caller decides missing-identity eligibility."""
    refused = {"stopped": False, "basis": "legacy_identity_unproven"}
    if not boot:
        return {**refused, "reason": "Windows boot time could not be independently verified"}
    try:
        cutoff = boot["time_ns"] - BOOT_FILE_MARGIN_NS
        if cutoff <= 0 or not job.get("created_at"):
            raise ValueError("Historical job creation time is unavailable")
        for name in ("created_at", "updated_at", "started_at", "finished_at"):
            if name in job:
                timestamp = datetime.fromisoformat(job[name])
                if timestamp.tzinfo is None or int(timestamp.timestamp() * 1e9) >= cutoff:
                    raise ValueError("Job timestamps do not predate the verified Windows boot")
        paths = sorted(directory.iterdir())
        if len(paths) > 64 or not all(
            (directory / n).is_file() for n in ("job.json", "request.json")
        ):
            raise ValueError("Historical job records are incomplete or exceed the evidence budget")
        paths = [directory, *paths]
        before = [_signature(path) for path in paths]
        if any(
            min(row["created_ns"], row["modified_ns"]) <= 0
            or max(row["created_ns"], row["modified_ns"]) >= cutoff
            for row in before
        ):
            raise ValueError("Job files do not predate the verified Windows boot")
        if before != [_signature(path) for path in paths] or paths[1:] != sorted(
            directory.iterdir()
        ):
            raise ValueError("Historical owner evidence changed during inspection")
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        return {**refused, "reason": str(error)}
    return {
        "stopped": True,
        "basis": "control_records_before_verified_windows_boot",
        "boot_started_at": boot["started_at"],
        "boot_time_ns": boot["time_ns"],
        "boot_source": boot["source"],
        "files": before,
    }

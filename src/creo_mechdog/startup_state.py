"""Validate shared startup metadata without treating damaged reservations as absent."""

from __future__ import annotations

import hashlib
import math
import os
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

MAX_STARTUP_STATE_BYTES = 1024 * 1024
BOOT_FILE_MARGIN_NS = 5_000_000_000


class StartupStateError(RuntimeError):
    def __init__(self, reason: str):
        self.payload = {
            "code": "startup_state_unreadable",
            "launch_state_known": False,
            "automatic_launch_allowed": False,
            "reason": reason,
            "recovery_required": (
                "Shared startup history cannot be trusted. Preserve state.json and existing "
                "job/model reservations; inspect pending launch dialogs and the configured Creo "
                "session. Retry may verify an existing session but cannot automatically launch "
                "a replacement until launch history is reconciled. Open Creo manually if needed."
            ),
        }
        super().__init__(f"Shared startup state is unreadable: {reason}")


def read_startup_state(path: Path, reader: Callable[[Path], dict]) -> dict:
    try:
        value = reader(path)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise StartupStateError(f"{type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise StartupStateError("Expected a JSON object")
    if not isinstance(value.get("state"), str) or not value["state"]:
        raise StartupStateError("Missing startup state")
    if "launch_reserved" not in value or "launch_attempt" not in value:
        raise StartupStateError("Missing launch reservation history")
    for key in ("connected", "launch_reserved"):
        if key in value and not isinstance(value[key], bool):
            raise StartupStateError(f"{key} must be boolean")
    attempt = value.get("launch_attempt", 0)
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 0:
        raise StartupStateError("launch_attempt must be a non-negative integer")
    deadline = value.get("phase_deadline_monotonic")
    if deadline is not None and (
        isinstance(deadline, bool)
        or not isinstance(deadline, (int, float))
        or not math.isfinite(deadline)
        or deadline < 0
    ):
        raise StartupStateError("phase_deadline_monotonic must be finite and non-negative")
    for key in ("state", "updated_at", "verified_at"):
        if key in value and not isinstance(value[key], str):
            raise StartupStateError(f"{key} must be a string")
    for key in ("updated_at", "verified_at"):
        if key in value:
            try:
                timestamp = datetime.fromisoformat(value[key])
                if timestamp.tzinfo is None:
                    raise ValueError("Timestamp has no timezone")
            except ValueError as exc:
                raise StartupStateError(f"{key} must be a timezone-aware ISO timestamp") from exc
    if "native" in value and not isinstance(value["native"], dict):
        raise StartupStateError("native must be a JSON object")
    return value


def archive_preboot_state(path: Path, boot: dict) -> dict:
    """Archive bytes before replacement; caller holds startup and Toolkit locks.

    Creation and modification must both precede a verified OS boot. A current
    boot's damaged reservation could still belong to a delayed desktop launch.
    This function never removes or replaces the source file.
    """
    before = path.stat()
    created_ns = getattr(before, "st_birthtime_ns", before.st_ctime_ns)
    if max(before.st_mtime_ns, created_ns) >= boot["time_ns"] - BOOT_FILE_MARGIN_NS:
        raise StartupStateError("Damaged startup history does not predate the verified OS boot")
    with path.open("rb") as stream:
        raw = stream.read(MAX_STARTUP_STATE_BYTES + 1)
    if len(raw) > MAX_STARTUP_STATE_BYTES:
        raise StartupStateError("Startup history exceeds the 1 MiB recovery limit")
    identity = (before.st_ino, before.st_size, before.st_mtime_ns, created_ns)
    after = path.stat()
    if identity != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        getattr(after, "st_birthtime_ns", after.st_ctime_ns),
    ):
        raise StartupStateError("Startup history changed during reconciliation")
    history = path.parent / "history"
    history.mkdir(exist_ok=True)
    archive = history / f"state-unreadable-{uuid.uuid4().hex}.bin"
    with archive.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Keep the archive even if a non-cooperating writer changes the source.
    current = path.stat()
    if identity != (
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
        getattr(current, "st_birthtime_ns", current.st_ctime_ns),
    ):
        raise StartupStateError("Startup history changed after backup; replacement was refused")
    return {
        "status": "reconciled_previous_boot",
        "basis": "creation_and_modification_before_verified_boot",
        "boot_started_at": boot["started_at"],
        "boot_source": boot["source"],
        "archive_file": str(archive),
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "original_bytes": len(raw),
        "job_model_reservations_preserved": True,
    }

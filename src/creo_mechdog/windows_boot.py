"""Bounded, read-only Windows reboot evidence for startup-history reconciliation."""

from __future__ import annotations

import ctypes
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BOOT_QUERY_BUDGET_SECONDS = 5


def boot_info() -> dict | None:
    """Cross-check documented WMI boot time against the kernel uptime clock.

    An unavailable provider, clock disagreement or malformed result cannot
    authorize replacing an unknown launch reservation. No estimated wall-clock
    boot timestamp is used alone as evidence of a reboot.
    """
    if os.name != "nt":
        return None
    executable = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    command = (
        "$ErrorActionPreference='Stop'; "
        "$b=(Get-CimInstance -ClassName Win32_OperatingSystem -Property LastBootUpTime "
        "-OperationTimeoutSec 3).LastBootUpTime; "
        "$b.ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)"
    )
    try:
        result = subprocess.run(
            [str(executable), "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            timeout=BOOT_QUERY_BUDGET_SECONDS,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=True,
        )
        started = datetime.fromisoformat(result.stdout.decode("ascii").strip())
        if started.tzinfo is None:
            return None
        ticks = ctypes.WinDLL("kernel32", use_last_error=True).GetTickCount64
        ticks.argtypes = []
        ticks.restype = ctypes.c_ulonglong
        uptime_seconds = ticks() / 1000
        now = datetime.now(timezone.utc)
        age = (now - started).total_seconds()
        # Tighter than the startup-file's five-second reboot margin: a clock
        # correction must not make a same-boot reservation look pre-boot.
        if age < 0 or abs(age - uptime_seconds) > 2:
            return None
        return {
            "started_at": started.astimezone(timezone.utc).isoformat(),
            "time_ns": int(started.timestamp() * 1_000_000_000),
            "source": "Win32_OperatingSystem.LastBootUpTime cross-checked with GetTickCount64",
            "query_budget_seconds": BOOT_QUERY_BUDGET_SECONDS,
            "clock_difference_seconds": age - uptime_seconds,
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        return None

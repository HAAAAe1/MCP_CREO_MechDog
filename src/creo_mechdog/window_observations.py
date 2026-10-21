"""Read-only top-level window observations; absence never proves a process is dead."""

from __future__ import annotations

import ctypes
from ctypes import wintypes


def _enumerate_windows(pids: set[int]) -> list[tuple[int, bool, bool]]:
    user = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    enumerate_windows = user.EnumWindows
    enumerate_windows.argtypes = (callback_type, wintypes.LPARAM)
    enumerate_windows.restype = wintypes.BOOL
    process_id = user.GetWindowThreadProcessId
    process_id.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    process_id.restype = wintypes.DWORD
    visible = user.IsWindowVisible
    visible.argtypes = (wintypes.HWND,)
    visible.restype = wintypes.BOOL
    hung = user.IsHungAppWindow
    hung.argtypes = (wintypes.HWND,)
    hung.restype = wintypes.BOOL
    rows = []

    @callback_type
    def observe(handle: int, parameter: int) -> bool:
        pid = wintypes.DWORD()
        if process_id(handle, ctypes.byref(pid)) and pid.value in pids:
            rows.append((pid.value, bool(visible(handle)), bool(hung(handle))))
        return True

    if not enumerate_windows(observe, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return rows


def window_observations(pids: set[int]) -> dict[int, dict]:
    """Inspect this desktop only; don't activate windows, read titles, or send messages."""
    if not pids:
        return {}
    try:
        rows = _enumerate_windows(pids)
    except OSError as error:
        return {
            pid: {"state": "unknown", "windows_error": getattr(error, "winerror", None)}
            for pid in pids
        }
    result = {}
    for pid in pids:
        owned = [(visible, hung) for owner, visible, hung in rows if owner == pid]
        count = sum(visible for visible, _ in owned)
        result[pid] = {
            "state": "visible" if count else "hidden_only" if owned else "none_observed",
            "top_level_count": len(owned),
            "visible_count": count,
            "hung_window_observed": any(hung for _, hung in owned),
            "visible_hung_window_observed": any(visible and hung for visible, hung in owned),
            "scope": "current Windows desktop; window absence does not prove process failure",
        }
    return result


def connection_guidance(snapshot: dict) -> str:
    matching = [p for p in snapshot.get("processes", []) if p.get("matches")]
    states = [p.get("windows", {}).get("state", "unknown") for p in matching]
    if any(p.get("windows", {}).get("visible_hung_window_observed") for p in matching):
        return "A matching Creo window was observed hung; preserve work and inspect that desktop/session."
    if states and all(s in ("hidden_only", "none_observed") for s in states):
        return (
            "Matching Creo processes have no visible top-level window on this desktop. "
            "Check the intended Windows desktop/session and startup state; this does not prove "
            "a dead process and does not authorize ending it."
        )
    if "visible" in states:
        return (
            "Check Creo for an active feature Dashboard or modal warning/dialog, finish or cancel "
            "it manually, then explicitly recheck readiness; a visible window does not prove Toolkit readiness."
        )
    return "Window state is unconfirmed; check the intended Creo session and startup dialogs before retrying."

"""Validation and diagnostics shared by the local native build entry points."""

from __future__ import annotations

import re
from pathlib import Path

COMPILER_ENV_KEYS = ("INCLUDE", "LIB", "PATH")
BUILD_LOG_TAIL_BYTES = 128 * 1024
_ERROR_LINE = re.compile(r"\b(?:fatal\s+)?error(?:\s+[A-Z]+\d+)?\s*:", re.IGNORECASE)


def validate_local_path(value: object, name: str) -> str:
    """Reject values that cannot be embedded in quoted cmd assignments."""
    if not isinstance(value, str) or not value.strip() or any(c in value for c in '\x00\r\n"%'):
        raise ValueError(f"Invalid local path: {name}")
    return value


def validate_compiler_env(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(COMPILER_ENV_KEYS):
        raise ValueError("vcvars64_env must contain exactly INCLUDE, LIB and PATH")
    return {
        key: validate_local_path(value[key], f"vcvars64_env.{key}") for key in COMPILER_ENV_KEYS
    }


def compiler_setup_script(settings: dict) -> str:
    """Use complete explicit values, or retain the original vcvars setup path."""
    env = validate_compiler_env(settings.get("vcvars64_env"))
    if env is not None:
        return "\n".join(f'set "{key}={env[key]}"' for key in COMPILER_ENV_KEYS)
    vcvars = validate_local_path(settings.get("vcvars64"), "vcvars64")
    return f'call "{vcvars}"\nif errorlevel 1 exit /b 1'


def read_build_log_tail(path: Path) -> str:
    """Bound failure-path I/O even when a compiler produces a very large log."""
    try:
        with path.open("rb") as stream:
            size = stream.seek(0, 2)
            offset = max(0, size - BUILD_LOG_TAIL_BYTES)
            stream.seek(offset)
            data = stream.read(BUILD_LOG_TAIL_BYTES)
        # Avoid reporting a partial first line as a complete compiler error.
        if offset:
            data = data.partition(b"\n")[2]
        return data.decode("utf-8", errors="replace")
    except OSError as exc:
        return f"error: build log could not be read ({type(exc).__name__})"


def diagnose_build_failure(returncode: int, log_text: str) -> str:
    if returncode == 0:
        return ""
    errors = [line for line in log_text.splitlines() if _ERROR_LINE.search(line)]
    constants = set()
    for line in errors:
        identifier = re.search(
            r"\berror\s+C2065\s*:\s*[^\w]*([A-Za-z_][A-Za-z0-9_]*)", line, re.IGNORECASE
        )
        if identifier and re.fullmatch(r"PRO_[A-Z0-9_]+", identifier[1]):
            constants.add(identifier[1])
    messages = []
    if constants:
        messages.append(
            "SDK version hint: "
            + ", ".join(sorted(constants))
            + " may require a newer Creo Toolkit SDK; the local SDK version may be too old."
        )
    messages.append("Build error summary (last 15 error lines):")
    messages.extend(errors[-15:] or ["No error-level lines found in the build log tail."])
    return "\n".join(messages)

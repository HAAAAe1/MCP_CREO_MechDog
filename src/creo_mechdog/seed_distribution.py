"""Canonical seed-library text bytes without changing native PRT payloads."""

from pathlib import Path


def seed_file_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix in {".md", ".json", ".py"} or path.name == "LICENSE":
        return data.replace(b"\r\n", b"\n")
    return data

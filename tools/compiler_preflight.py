"""Check the environment produced by vcvars64 before invoking cl/link.

Some sandboxes (this machine included) hand child processes a rewritten PATH:
vcvars64 sets PATH correctly inside the batch file, INCLUDE/LIB propagate, but the
inherited PATH that reaches cl.exe/link.exe is replaced with the host's own value,
so a plain ``shutil.which`` reports a false negative. When PATH lookup fails we fall
back to the MSVC/SDK directories taken from INCLUDE and LIB, which do propagate.
"""

import os
from pathlib import Path
import shutil


def _sibling_bin_dirs(env: dict[str, str]) -> list[Path]:
    r"""Derive MSVC tool directories from the propagated INCLUDE/LIB values.

    INCLUDE contains ``<VC>\Tools\MSVC\<ver>\include``; its parent holds ``bin``.
    LIB contains ``<SDK>\lib\<ver>\ucrt\x64`` and ``<SDK>\lib\<ver>\um\x64``; the
    SDK ``bin\<ver>\x64`` directory sits beside them.
    """
    candidates: list[Path] = []
    for root in (env.get("INCLUDE", ""), env.get("LIB", "")):
        for entry in root.split(";"):
            entry = entry.strip().strip('"')
            if not entry:
                continue
            path = Path(entry)
            # MSVC: ...\VC\Tools\MSVC\<ver>\include -> ...\VC\Tools\MSVC\<ver>\bin\HostX64\x64
            if path.name.lower() == "include" and path.parent.joinpath("bin").is_dir():
                for host in ("HostX64", "Hostx64"):
                    tool_bin = path.parent / "bin" / host / "x64"
                    if tool_bin.is_dir():
                        candidates.append(tool_bin)
            # SDK: ...\Windows Kits\10\lib\<ver>\ucrt\x64 -> ...\Windows Kits\10\bin\<ver>\x64
            if path.name.lower() == "x64" and path.parent.name.lower() == "ucrt":
                version_dir = path.parent.parent
                if version_dir.parent.name.lower() == "lib":
                    sdk_root = version_dir.parent.parent
                    bin_dir = sdk_root / "bin" / version_dir.name / "x64"
                    if bin_dir.is_dir():
                        candidates.append(bin_dir)
    return candidates


def compiler_environment_errors(env: dict[str, str]) -> list[str]:
    errors = []
    path = env.get("PATH", "")
    fallbacks = _sibling_bin_dirs(env)
    for program in ("cl.exe", "link.exe"):
        if shutil.which(program, path=path):
            continue
        if any((directory / program).is_file() for directory in fallbacks):
            continue
        errors.append(f"{program} is unavailable after vcvars64; install MSVC x64 tools")
    include = [Path(p.strip('"')) for p in env.get("INCLUDE", "").split(";") if p]
    libraries = [Path(p.strip('"')) for p in env.get("LIB", "").split(";") if p]
    for filename, label in (
        ("stdio.h", "Windows SDK UCRT headers"),
        ("windows.h", "Windows SDK UM headers"),
    ):
        if not any((directory / filename).is_file() for directory in include):
            errors.append(f"Missing {filename} in INCLUDE: {label} were not configured")
    for filename in ("ucrt.lib", "kernel32.lib"):
        if not any((directory / filename).is_file() for directory in libraries):
            errors.append(
                f"Missing {filename} in LIB: Windows SDK x64 libraries were not configured"
            )
    if errors:
        errors.append(
            "Check Visual Studio C++/Windows SDK installation and vcvars64 SDK discovery; blocked reg.exe/registry access can cause this even when vcvars64 exits 0. Ask the environment administrator to allow SDK discovery, or pass a reviewed local compiler environment wrapper via -VcVars64. Global security policy is not changed by this installer."
        )
    return errors


if __name__ == "__main__":
    problems = compiler_environment_errors(dict(os.environ))
    for problem in problems:
        print("COMPILER_PREFLIGHT: " + problem)
    if not problems:
        print("COMPILER_PREFLIGHT: MSVC, UCRT and Windows SDK headers/libraries found")
    raise SystemExit(4 if problems else 0)

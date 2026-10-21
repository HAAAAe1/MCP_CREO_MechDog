"""BUG-036: compile actual SDK declarations with substituted transform APIs (no Creo)."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from creo_mechdog.build_support import compiler_setup_script, validate_local_path
from creo_mechdog.paths import SOURCE_PATHS


def main() -> int:
    root = SOURCE_PATHS.resource_root
    settings = json.loads((root / "config.json").read_text(encoding="utf-8-sig"))
    sdk = Path(settings["creo_root"]) / "Common Files/protoolkit/includes"
    directory = root / "build/component_transform_test"
    directory.mkdir(parents=True, exist_ok=True)
    source = root / "tests/native/test_component_transform.cpp"
    executable = directory / "component_transform_test.exe"
    for path in (sdk, directory, root / "native", source):
        validate_local_path(str(path), "component transform contract test path")
    batch = directory / "build.cmd"
    batch.write_text(
        "@echo off\n"
        + compiler_setup_script(settings)
        + f'\ncl /nologo /std:c++17 /EHsc /W3 /I "{sdk}" /I "{root / "native"}" '
        + f'/Fo:"{directory / "contract.obj"}" /Fe:"{executable}" "{source}"\n'
        + "exit /b %errorlevel%\n",
        encoding="utf-8",
    )
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with (directory / "build.log").open("wb") as log:
        built = subprocess.run(
            ["cmd.exe", "/d", "/c", str(batch)],
            cwd=directory,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=90,
            creationflags=flags,
        )
    passed = built.returncode == 0
    if passed:
        passed = (
            subprocess.run(
                [str(executable)], cwd=directory, timeout=10, creationflags=flags
            ).returncode
            == 0
        )
    report = {
        "work_item": "BUG-036",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sdk": str(sdk),
        "success": passed,
        "cases": 7,
        "toolkit_connected": False,
        "scope": "SDK contract only; substituted results do not verify solved geometry or save/reload",
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

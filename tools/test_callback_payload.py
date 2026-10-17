"""Run the compiled payload against a fixture host API; no Creo connection or geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import bridge
from tools.dev_check import git_state, source_hash

ROOT = Path(__file__).resolve().parents[1]


def run(output: Path) -> dict:
    build = ROOT / "build"
    setup = bridge.read_json(build / "blend_callback_setup.json")
    settings = bridge.config()
    sdk = Path(settings["creo_root"]) / "Common Files/protoolkit"
    # A nested checkout plus SHA256 directories can exceed the Toolkit/MAX_PATH
    # limit. Keep this standalone fixture short and retain it for diagnosis.
    fixture_parent = ROOT / "build" / "cb_abi"
    fixture_parent.mkdir(parents=True, exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix="run_", dir=fixture_parent))
    source_module = Path(setup["module_file"])
    module = fixture / "build/blend_callback" / setup["dll_sha256"] / "callback.dll"
    module.parent.mkdir(parents=True)
    shutil.copyfile(source_module, module)
    bootstrap = bridge.read_json(source_module.parent / "callback_bootstrap.json")
    bootstrap["resource_root"] = str(fixture)
    bridge.write_json(module.parent / "callback_bootstrap.json", bootstrap)
    loader = fixture / "build/blend_loader" / setup["loader_fingerprint"] / "loader.dll"
    loader.parent.mkdir(parents=True)
    shutil.copyfile(setup["loader_file"], loader)
    request = fixture / "jobs/fixture/callback_request.json"
    request.parent.mkdir(parents=True)
    bridge.write_json(request, {"protocol": 3, "model_name": "fixture_model", "curve_ids": [1, 2]})
    executable = fixture / "payload_test.exe"
    source = ROOT / "tools/test_callback_payload.cpp"
    libraries = " ".join(
        f'"{sdk / "x86e_win64/obj" / name}"'
        for name in ("protkmd_NU.lib", "ptasyncmd.lib", "ucore.lib", "udata.lib")
    )
    script = fixture / "build.cmd"
    script.write_text(
        f'''@echo off
{bridge.compiler_setup_script(settings)}
if errorlevel 1 exit /b 1
cl /nologo /MD /EHsc /std:c++17 /W3 /DPRO_MACHINE=36 /DPRO_OS=4 /I"{sdk / "includes"}" /c "{source}" /Fo"{fixture / "payload_test.obj"}"
if errorlevel 1 exit /b 2
link /nologo /MACHINE:X64 /OUT:"{executable}" "{fixture / "payload_test.obj"}" {libraries} kernel32.lib user32.lib wsock32.lib advapi32.lib mpr.lib winspool.lib netapi32.lib psapi.lib gdi32.lib shell32.lib comdlg32.lib ole32.lib ws2_32.lib
''',
        encoding="utf-8",
    )
    with (fixture / "build.log").open("wb") as log:
        subprocess.run(
            ["cmd.exe", "/d", "/c", str(script)],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=90,
            creationflags=bridge.HIDDEN,
            check=True,
        )
    raw = fixture / "result.json"
    subprocess.run(
        [str(executable), str(module), str(loader), str(request), str(raw)],
        cwd=ROOT,
        env=bridge.native_environment(),
        timeout=20,
        creationflags=bridge.HIDDEN,
        check=True,
    )
    report = {
        "work_item": "FEAT-029",
        "timestamp": bridge.now(),
        "source": git_state(ROOT),
        "source_fingerprints": {
            str(p.relative_to(ROOT)): source_hash(p)
            for p in (
                source,
                Path(__file__),
                ROOT / "native/blend_sync.cpp",
                ROOT / "native/callback_api.h",
            )
        },
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "creo_sdk": str(sdk),
            "creo_session": "not connected",
        },
        "payload_sha256": hashlib.sha256(source_module.read_bytes()).hexdigest(),
        "fixture": str(fixture),
        "result": bridge.read_json(raw),
        "scope": "SDK allocation and fixture-model host API only; not Creo or WorkBuddy acceptance",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    bridge.write_json(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/feat029-payload-abi.json")
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps(report["result"], ensure_ascii=False))
    return 0 if report["result"]["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

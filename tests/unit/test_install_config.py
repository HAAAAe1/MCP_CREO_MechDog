import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog.build_support import compiler_setup_script

ROOT = Path(__file__).resolve().parents[2]


class InstallConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.settings = {
            "creo_root": str(self.root / "Creo"),
            "vcvars64": str(self.root / "missing.bat"),
            "vcvars64_env": {"INCLUDE": "inc", "LIB": "lib", "PATH": "bin"},
        }

    def config(self):
        (self.root / "config.json").write_text(json.dumps(self.settings), encoding="utf-8")
        with patch.object(bridge, "ROOT", self.root):
            return bridge.config()

    def sdk(self):
        for relative in (
            "Parametric/bin/parametric.exe",
            "Common Files/protoolkit/includes/ProToolkit.h",
            "Common Files/x86e_win64/obj/pro_comm_msg.exe",
            "Common Files/templates/mmns_part_solid_abs.prt",
            "Common Files/templates/mmns_asm_design_abs.asm",
            *[
                f"Common Files/protoolkit/x86e_win64/obj/{name}.lib"
                for name in ("ptasyncmd", "protkmd_NU", "protk_dllmd_NU", "ucore", "udata")
            ],
        ):
            path = Path(self.settings["creo_root"]) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    def test_env_requires_exact_nonempty_string_values_and_rejects_injection(self):
        for invalid in (
            {},
            [],
            "INCLUDE=inc",
            {"INCLUDE": "inc", "LIB": "lib"},
            dict(self.settings["vcvars64_env"], EXTRA="bad"),
            {"include": "inc", "LIB": "lib", "PATH": "bin"},
            *[
                dict(self.settings["vcvars64_env"], PATH=value)
                for value in (None, 1, "", " ", 'a"b', "%PATH%", "a\nb", "a\rb", "a\0b")
            ],
        ):
            with self.subTest(invalid=invalid):
                original = self.settings["vcvars64_env"]
                self.settings["vcvars64_env"] = invalid
                with self.assertRaisesRegex(ValueError, "vcvars64_env"):
                    self.config()
                self.settings["vcvars64_env"] = original

    def test_explicit_env_does_not_require_vcvars_and_missing_sdk_still_fails(self):
        self.sdk()
        self.settings.pop("vcvars64")
        self.config()
        with patch.object(bridge, "ROOT", self.root):
            result = bridge.check_environment()
            self.assertTrue(result["ready_to_build"])
            self.assertEqual(result["checks"]["compiler_setup"]["source"], "vcvars64_env")
            self.assertIn("unverified_here", result["compiler_environment"])
            (Path(self.settings["creo_root"]) / "Parametric/bin/parametric.exe").unlink()
            self.assertFalse(bridge.check_environment()["ready_to_build"])

    def test_absent_and_null_env_keep_legacy_file_check(self):
        self.sdk()
        for absent in (False, True):
            self.settings["vcvars64_env"] = None
            if absent:
                self.settings.pop("vcvars64_env")
            value = self.config()
            self.assertIsNone(value["vcvars64_env"])
            with patch.object(bridge, "ROOT", self.root):
                self.assertFalse(bridge.check_environment()["ready_to_build"])
        self.assertIn('call "', compiler_setup_script(value))

    def test_build_uses_explicit_env_preflight_and_includes_failure_summary(self):
        self.sdk()
        (self.root / "native").mkdir()
        (self.root / "native/worker.cpp").write_text("// fixture")
        self.config()

        def run(command, **kwargs):
            if command[0] == "cmd.exe":
                kwargs["stdout"].write(b"worker.cpp: error C2065: PRO_NEW_CONSTANT\n")
                return subprocess.CompletedProcess(command, 2)
            return subprocess.CompletedProcess(command, 0)

        with (
            patch.object(bridge, "ROOT", self.root),
            patch.object(bridge.subprocess, "run", side_effect=run),
        ):
            with self.assertRaisesRegex(RuntimeError, "SDK version hint"):
                bridge.build_native()
        script = (self.root / "build/build.cmd").read_text()
        self.assertIn('set "INCLUDE=inc"', script)
        self.assertIn('set "LIB=lib"', script)
        self.assertIn('set "PATH=bin"', script)
        self.assertIn("DisableDelayedExpansion", script)
        self.assertNotIn('call "', script)
        self.assertIn("compiler_preflight.py", script)
        self.assertLess(script.index('set "PATH='), script.index("compiler_preflight.py"))

    @unittest.skipUnless(os.name == "nt", "Windows cmd assignment semantics")
    def test_quoted_assignment_preserves_metacharacters_and_exclamation(self):
        env = {
            key: "C:\\path with spaces & echo unsafe!^;C:\\other"
            for key in ("INCLUDE", "LIB", "PATH")
        }
        script = self.root / "check.cmd"
        script.write_text(
            "@echo off\nsetlocal DisableDelayedExpansion\n"
            + compiler_setup_script({"vcvars64_env": env})
            + f"\n\"{sys.executable}\" -c \"import os,json; print(json.dumps(dict((k,os.environ[k]) for k in ('INCLUDE','LIB','PATH'))))\"\n"
        )
        result = subprocess.run(
            ["cmd.exe", "/d", "/v:on", "/c", str(script)],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
            creationflags=bridge.HIDDEN,
        )
        self.assertEqual(json.loads(result.stdout), env)

    def powershell(self, arguments, *, env=None):
        def quote(value):
            return "'" + str(value).replace("'", "''") + "'"

        command = f"& {quote(self.root / 'setup.ps1')} " + arguments
        encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
        return subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            env=env,
            capture_output=True,
            timeout=20,
            creationflags=bridge.HIDDEN,
        )

    def installer(self):
        self.sdk()
        self.settings["local_extra"] = {"retained": True}
        self.config()
        shutil.copy2(ROOT / "setup.ps1", self.root / "setup.ps1")

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell installer")
    def test_setup_env_config_checkonly_and_parameter_writeback(self):
        self.installer()
        before = (self.root / "config.json").read_bytes()
        real_python = sys._base_executable.replace("'", "''")
        result = self.powershell(f"-Python '{real_python}' -CheckOnly")
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.assertEqual(before, (self.root / "config.json").read_bytes())
        # Stop after configuration is persisted, before any venv/dependency changes.
        fake = self.root / "python.cmd"
        fake.write_text(
            '@echo off\nif "%~1"=="-c" (\necho {"version":[3,12,0],"bits":64}\nexit /b 0\n)\nexit /b 1\n'
        )
        result = self.powershell(
            f"-Python '{fake}' -VcVars64Env @{{INCLUDE='new inc';LIB='new lib';PATH='new bin'}}"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"Python virtual environment", result.stdout)
        saved = json.loads((self.root / "config.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(
            saved["vcvars64_env"], {"INCLUDE": "new inc", "LIB": "new lib", "PATH": "new bin"}
        )
        self.assertEqual(saved["local_extra"], {"retained": True})
        self.assertFalse((self.root / ".venv").exists())

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell installer")
    def test_setup_rejects_invalid_env_and_explicit_vcvars_overrides_saved_env(self):
        self.installer()
        for value in (
            "@{}",
            "@{INCLUDE='i';LIB='l';PATH='%PATH%'}",
            "@{include='i';LIB='l';PATH='p'}",
        ):
            result = self.powershell(f"-VcVars64Env {value} -CheckOnly")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"vcvars64_env", result.stderr)
        result = self.powershell(f"-VcVars64 '{self.root / 'missing.bat'}' -CheckOnly")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"vcvars64.bat not found", result.stderr)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell installer")
    def test_setup_rejects_windowsapps_before_executing_explicit_or_discovered_python(self):
        self.installer()
        windowsapps = self.root / "WindowsApps"
        windowsapps.mkdir()
        placeholder = windowsapps / "python.exe"
        placeholder.touch()
        for explicit in (False, True):
            env = dict(os.environ)
            env["PATH"] = str(windowsapps)
            result = self.powershell(
                (f"-Python '{placeholder}' " if explicit else "") + "-CheckOnly", env=env
            )
            self.assertNotEqual(result.returncode, 0)
            for message in (b"WindowsApps", b"placeholder", b"-Python"):
                self.assertIn(message, result.stderr)

"""DEV-002 source layout, installation identity and stable data path guards."""

import asyncio
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge
import server
from creo_mechdog import capability_pages, update_check
from creo_mechdog.paths import SOURCE_PATHS, ProjectPaths
from tools import package
from version import VERSION

ROOT = Path(__file__).resolve().parents[2]


class SourceLayoutTests(unittest.TestCase):
    def test_package_is_loaded_from_src_and_root_copy_is_absent(self):
        self.assertEqual(
            Path(update_check.__file__).resolve(), ROOT / "src/creo_mechdog/update_check.py"
        )
        self.assertFalse((ROOT / "update_check.py").exists())
        self.assertIsNone(importlib.util.find_spec("update_check"))

    def test_default_data_paths_match_existing_bridges(self):
        self.assertEqual(SOURCE_PATHS.code_root, ROOT / "src/creo_mechdog")
        self.assertEqual(SOURCE_PATHS.resource_root, ROOT)
        self.assertEqual(SOURCE_PATHS.data_root, bridge.ROOT)
        self.assertEqual(SOURCE_PATHS.jobs, bridge.JOBS)
        with patch.object(bridge, "config", return_value={}):
            # Local design: generic_bridge.MODELS=None means "resolve from config";
            # assert the default layout (no model_root override) matches SOURCE_PATHS.
            self.assertEqual(SOURCE_PATHS.models, generic_bridge.models_root())
        self.assertEqual(SOURCE_PATHS.build, ROOT / "build")

    def test_explicit_data_root_is_independent_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            source = parent / "source checkout"
            data = parent / "runtime data"
            paths = ProjectPaths.source_checkout(source, data_root=data)
            self.assertEqual(paths.code_root, source / "src/creo_mechdog")
            self.assertEqual(paths.resource_root, source)
            self.assertEqual(paths.models, data / "models")
            self.assertEqual(paths.jobs, data / "jobs")
            self.assertEqual(list(parent.iterdir()), [])

    def test_standard_install_supports_import_from_unrelated_working_directory(self):
        code = """
import json,version
from creo_mechdog import update_check
from creo_mechdog.paths import SOURCE_PATHS
print(json.dumps({'module':update_check.__file__,'version_file':version.__file__,
 'version':version.VERSION,'resource_root':str(SOURCE_PATHS.resource_root),
 'data_root':str(SOURCE_PATHS.data_root)}))
"""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
        value = json.loads(result.stdout)
        self.assertEqual(Path(value["module"]), ROOT / "src/creo_mechdog/update_check.py")
        self.assertEqual(Path(value["version_file"]), ROOT / "version.py")
        self.assertEqual(value["version"], VERSION)
        self.assertEqual(Path(value["resource_root"]), ROOT)
        self.assertEqual(Path(value["data_root"]), ROOT)

    def test_server_rejects_package_from_another_checkout(self):
        code = """
from pathlib import Path
from creo_mechdog import paths
paths.SOURCE_PATHS = paths.ProjectPaths.source_checkout(Path('wrong-checkout'))
try:
 import server
except RuntimeError as exc:
 assert 'another source checkout' in str(exc)
else:
 raise AssertionError('mixed source copies must not initialize the service')
"""
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, capture_output=True, timeout=15
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_identifies_roots_and_migrated_source(self):
        capability_pages.reset_snapshot()
        page = asyncio.run(server.creo_capabilities(detail="full", section="runtime"))
        runtime = {entry["key"]: entry["value"] for entry in page["entries"]}
        self.assertEqual(Path(runtime["code_root"]), ROOT)
        self.assertEqual(Path(runtime["python_package_root"]), SOURCE_PATHS.code_root)
        self.assertEqual(Path(runtime["resource_root"]), SOURCE_PATHS.resource_root)
        self.assertEqual(Path(runtime["data_root"]), SOURCE_PATHS.data_root)
        self.assertIn("src/creo_mechdog/update_check.py", runtime["source_fingerprints_at_startup"])
        self.assertNotIn("update_check.py", runtime["source_fingerprints_at_startup"])
        self.assertFalse(runtime["source_changed_since_startup"])

    def test_source_archive_contains_package_and_nested_tests_without_metadata(self):
        names = {p.relative_to(ROOT).as_posix() for p in package.source_files()}
        self.assertTrue(
            {
                "src/creo_mechdog/__init__.py",
                "src/creo_mechdog/paths.py",
                "src/creo_mechdog/update_check.py",
                "tests/unit/__init__.py",
                "tests/unit/test_update_check.py",
                "tests/unit/test_paths.py",
            }
            <= names
        )
        self.assertNotIn("update_check.py", names)
        self.assertFalse(any(".egg-info/" in name or "__pycache__/" in name for name in names))


if __name__ == "__main__":
    unittest.main()

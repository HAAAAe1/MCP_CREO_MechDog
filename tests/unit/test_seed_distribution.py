import contextlib
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import bridge
import seeds
from tools import package_seeds
from version import VERSION


class SeedDistributionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.native = b"native\x00\r\n\xffPRT"

    def fixture(self, name, newline):
        root = self.temp / name
        library = root / "seed_library"
        (library / "seeds").mkdir(parents=True)
        (root / "docs").mkdir()
        manifest = {
            "compatible_server_version": VERSION,
            "seeds": [
                {
                    "name": "fixture",
                    "seed_feature_id": 9,
                    "section_count": 2,
                    "relative_path": "seeds/example.prt.1",
                    "sha256": hashlib.sha256(self.native).hexdigest(),
                }
            ],
        }
        for path, text in (
            (root / "LICENSE", "MIT fixture\nCopyright fixture\n"),
            (library / "LICENSE", "MIT fixture\nCopyright fixture\n"),
            (library / "README.md", "# Fixture\nSeed description\n"),
            (library / "seed_manifest.json", json.dumps(manifest, indent=2) + "\n"),
            (root / "docs/seed_manifest.json", json.dumps(manifest, indent=2) + "\n"),
        ):
            path.write_bytes(text.replace("\n", newline).encode())
        (library / "seeds/example.prt.1").write_bytes(self.native)
        return root, library, manifest

    def test_seed_zip_identical_across_text_newlines_and_native_bytes_preserved(self):
        archives = []
        for name, newline in (("lf", "\n"), ("crlf", "\r\n")):
            root, library, _ = self.fixture(name, newline)
            output = self.temp / (name + ".zip")
            files = sorted(path for path in library.rglob("*") if path.is_file())
            with (
                patch.object(package_seeds, "ROOT", root),
                patch.object(package_seeds, "source_files", return_value=files),
                patch("sys.argv", ["package_seeds.py", "--output", str(output)]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                package_seeds.main()
            archives.append(output.read_bytes())
            with zipfile.ZipFile(output) as archive:
                prefix = f"MCP_CREO_MechDog-{VERSION}-seed-library/"
                self.assertEqual(archive.read(prefix + "seeds/example.prt.1"), self.native)
                self.assertNotIn(b"\r\n", archive.read(prefix + "seed_manifest.json"))
            self.assertEqual((library / "seeds/example.prt.1").read_bytes(), self.native)
        self.assertEqual(archives[0], archives[1])

    def test_license_comparison_accepts_newline_difference_but_rejects_changed_terms(self):
        root, library, manifest = self.fixture("license", "\r\n")
        (root / "LICENSE").write_bytes(b"MIT fixture\nCopyright fixture\n")
        with (
            patch.object(bridge, "ROOT", root),
            patch.object(seeds, "manifest", return_value=manifest),
        ):
            seeds._validate_library(library)
            (library / "LICENSE").write_bytes(b"Changed license terms\r\n")
            with self.assertRaisesRegex(ValueError, "MIT license"):
                seeds._validate_library(library)

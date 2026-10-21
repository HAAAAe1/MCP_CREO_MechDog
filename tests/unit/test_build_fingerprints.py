import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog import build_fingerprints
from tools.generate_constants import HEADERS, generate

ROOT = Path(__file__).resolve().parents[2]


class FingerprintFunctionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def snapshot(self, name, newline):
        directory = self.root / name
        directory.mkdir()
        (directory / "a.cpp").write_bytes(f"int one();{newline}line two{newline}".encode())
        (directory / "b.hpp").write_bytes(f"header{newline}more".encode())
        return build_fingerprints.read_dependency_snapshot(directory, ("a.cpp", "b.hpp"))

    def test_line_ending_only_change_keeps_normalized_fingerprint(self):
        crlf = self.snapshot("crlf", "\r\n")
        lf = self.snapshot("lf", "\n")
        self.assertEqual(
            build_fingerprints.normalized_digest(b"p", b"", crlf),
            build_fingerprints.normalized_digest(b"p", b"", lf),
        )

        def raw_digest(snapshot):
            digest = hashlib.sha256(b"p")
            for relative, data in snapshot.items():
                digest.update(relative.encode() + data)
            return digest.hexdigest()

        candidates = build_fingerprints.legacy_digest_candidates(b"p", b"", lf)
        self.assertIn(raw_digest(crlf), candidates)
        self.assertIn(raw_digest(lf), candidates)

    def test_real_content_change_always_changes_fingerprint(self):
        first = self.snapshot("lf", "\n")
        path = next(iter(first))
        changed = {**first, path: first[path].replace(b"one", b"two")}
        self.assertNotEqual(
            build_fingerprints.normalized_digest(b"p", b"", first),
            build_fingerprints.normalized_digest(b"p", b"", changed),
        )
        self.assertNotIn(
            hashlib.sha256(b"p" + path.encode() + changed[path]).hexdigest(),
            build_fingerprints.legacy_digest_candidates(b"p", b"", first),
        )

    def test_cache_matching_accepts_algorithm_marker_and_legacy_equivalence(self):
        current = "c" * 64
        legacy = "l" * 64
        self.assertEqual(
            build_fingerprints.match_cached_fingerprint(
                {"algorithm": build_fingerprints.FINGERPRINT_ALGORITHM, "fingerprint": current},
                current,
                set(),
            ),
            (True, current),
        )
        stored_generation = "g" * 64
        self.assertEqual(
            build_fingerprints.match_cached_fingerprint(
                {
                    "algorithm": build_fingerprints.FINGERPRINT_ALGORITHM,
                    "fingerprint": current,
                    "generation_key": stored_generation,
                },
                current,
                set(),
            ),
            (True, stored_generation),
        )
        self.assertEqual(
            build_fingerprints.match_cached_fingerprint({"fingerprint": legacy}, current, {legacy}),
            (True, legacy),
        )
        for mismatch in (
            {},
            None,
            {"algorithm": build_fingerprints.FINGERPRINT_ALGORITHM, "fingerprint": "x" * 64},
            {"fingerprint": "z" * 64},
            {"fingerprint": 123},
        ):
            self.assertEqual(
                build_fingerprints.match_cached_fingerprint(mismatch, current, {legacy}),
                (False, None),
            )


class BuildNativeMigrationTests(unittest.TestCase):
    """Loader/callback generations survive a line-ending-only source change."""

    RELATIVES = (
        "native/blend_sync.cpp",
        "native/blend_loader.cpp",
    )

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.creo = self.root / "Creo"
        includes = self.creo / "Common Files/protoolkit/includes"
        includes.mkdir(parents=True)
        for header in HEADERS:
            (includes / header).write_text("// fixture\n", encoding="utf-8")
        self.settings = {
            "creo_root": str(self.creo),
            "vcvars64_env": {"INCLUDE": "i", "LIB": "l", "PATH": "p"},
        }
        (self.root / "config.json").write_text(json.dumps(self.settings), encoding="utf-8")
        self.native = self.root / "native"
        self.native.mkdir()
        for name in ("worker.cpp", "blend_sync.cpp", "blend_loader.cpp"):
            (self.native / name).write_bytes(b"// source\r\nwith crlf\r\n")
        self.compiles = 0
        self.build_round = 0

        def counting_run(command, **kwargs):
            if len(command) > 1 and command[1].endswith("generate_constants.py"):
                generate(self.root)
            elif command[0] == "cmd.exe":
                self.compiles += 1
                self.build_round += 1
                script = (self.root / "build/build.cmd").read_text()
                if "blend_sync.cpp" in script:
                    (self.root / "build/creo_blend_sync.dll").write_bytes(
                        f"callback image r{self.build_round}".encode()
                    )
                if "blend_loader.cpp" in script:
                    (self.root / "build/creo_blend_loader.dll").write_bytes(
                        f"loader image r{self.build_round}".encode()
                    )
                (self.root / "build/creo_worker.exe").write_bytes(b"worker image")
            return subprocess.CompletedProcess(command, 0, stdout=b"{}")

        for patcher in (
            patch.object(bridge, "ROOT", self.root),
            patch.object(bridge, "config", return_value=self.settings),
            patch.object(bridge, "check_environment", return_value={"ready_to_build": True}),
            patch.object(bridge.subprocess, "run", side_effect=counting_run),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def legacy_loader_fingerprint(self):
        """Recompute the pre-normalization raw-byte loader fingerprint (v1)."""
        return self._legacy_fingerprint(b"MSVC17_MD_LOADER_v1", "native/blend_loader.cpp")

    def legacy_callback_fingerprint(self):
        """Recompute the pre-normalization raw-byte callback fingerprint (v1)."""
        return self._legacy_fingerprint(b"MSVC17_MD_DLL_v1", "native/blend_sync.cpp")

    def _legacy_fingerprint(self, prefix: bytes, leader: str) -> str:
        includes = Path(self.settings["creo_root"]) / "Common Files/protoolkit/includes"
        abi = hashlib.sha256()
        for p in sorted(includes.rglob("*.h")):
            abi.update(
                b"\0SDK_HEADER\0" + p.relative_to(includes).as_posix().encode() + p.read_bytes()
            )
        abi.update(json.dumps(self.settings, sort_keys=True).encode())
        digest = hashlib.sha256(prefix + abi.digest())
        for relative in (
            leader,
            "native/callback_identity.h",
            "native/callback_api.h",
            "native/third_party/json.hpp",
        ):
            source = self.root / relative
            if source.is_file():
                digest.update(relative.encode() + source.read_bytes())
        return digest.hexdigest()

    def setup_metadata(self):
        return bridge.read_json(self.root / "build/blend_callback_setup.json")

    def seed_legacy_installation(self):
        """Reproduce a 0.4.x build: raw-byte caches, immutable loader generation."""
        legacy_loader = self.legacy_loader_fingerprint()
        legacy_callback = self.legacy_callback_fingerprint()
        loader_sha = hashlib.sha256(b"loader image").hexdigest()
        callback_sha = hashlib.sha256(b"callback image").hexdigest()
        build = self.root / "build"
        pinned = build / "blend_loader" / legacy_loader
        pinned.mkdir(parents=True)
        (pinned / "loader.dll").write_bytes(b"loader image")
        (build / "creo_blend_loader.dll").write_bytes(b"loader image")
        (build / "creo_blend_sync.dll").write_bytes(b"callback image")
        (build / "creo_worker.exe").write_bytes(b"worker image")
        (build / "blend_loader_build.json").write_text(
            json.dumps({"fingerprint": legacy_loader, "sha256": loader_sha})
        )
        (build / "blend_sync_build.json").write_text(
            json.dumps({"fingerprint": legacy_callback, "sha256": callback_sha})
        )
        (build / "source.sha256").write_text("legacy raw-byte worker digest")
        return legacy_loader, loader_sha

    def test_legacy_cache_survives_line_ending_flip_without_new_generation(self):
        legacy, loader_sha = self.seed_legacy_installation()
        # A git checkout flips every source file to LF-only endings.
        for name in ("worker.cpp", "blend_sync.cpp", "blend_loader.cpp"):
            path = self.native / name
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        bridge.build_native()

        # The legacy generation was proven equivalent and reused, not rebuilt.
        cache = bridge.read_json(self.root / "build/blend_loader_build.json")
        self.assertEqual(cache["algorithm"], build_fingerprints.FINGERPRINT_ALGORITHM)
        self.assertEqual(cache["generation_key"], legacy)
        setup = self.setup_metadata()
        self.assertEqual(setup["loader_fingerprint"], legacy)
        self.assertEqual(setup["loader_sha256"], loader_sha)
        registry = (self.root / "build/blend_loader" / legacy / "protk.dat").read_text()
        self.assertIn(legacy, registry)
        # No new loader generation directory appeared; only the worker was
        # recompiled for the algorithm switch.
        self.assertEqual(
            [entry.name for entry in (self.root / "build/blend_loader").iterdir()], [legacy]
        )
        self.assertEqual(self.compiles, 1)
        script = (self.root / "build/build.cmd").read_text()
        self.assertNotIn("blend_loader.cpp", script)
        self.assertNotIn("blend_sync.cpp", script)
        # The build after migration hits the fully verified fast path.
        bridge.build_native()
        self.assertEqual(self.compiles, 1)
        self.assertEqual(
            (self.root / "build/blend_loader" / legacy / "protk.dat").read_text(), registry
        )

    def test_line_ending_flip_keeps_worker_cache_too(self):
        bridge.build_native()
        first_stamp = (self.root / "build/source.sha256").read_text()
        for name in ("worker.cpp", "blend_sync.cpp", "blend_loader.cpp"):
            path = self.native / name
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        bridge.build_native()
        # Normalized worker fingerprints ignore the line-ending flip entirely.
        self.assertEqual((self.root / "build/source.sha256").read_text(), first_stamp)
        self.assertEqual(self.compiles, 1)

    def test_unprovable_legacy_cache_rebuilds_into_new_generation(self):
        bridge.build_native()
        loader_sha = self.setup_metadata()["loader_sha256"]
        # A legacy cache whose fingerprint matches nothing (contents changed).
        (self.root / "build/blend_loader_build.json").write_text(
            json.dumps({"fingerprint": "f" * 64, "sha256": loader_sha})
        )
        (self.native / "blend_loader.cpp").write_bytes(b"// actually changed\r\n")
        bridge.build_native()
        cache = bridge.read_json(self.root / "build/blend_loader_build.json")
        self.assertEqual(cache["algorithm"], build_fingerprints.FINGERPRINT_ALGORITHM)
        self.assertNotEqual(cache["generation_key"], "f" * 64)
        self.assertEqual(self.setup_metadata()["loader_fingerprint"], cache["generation_key"])

    def test_interrupted_metadata_publish_leaves_no_false_success(self):
        bridge.build_native()
        stamp = self.root / "build/source.sha256"
        stamp.unlink()

        def failing(build, dll_sha256, loader_fingerprint):
            raise ValueError("publish interrupted")

        with patch.object(bridge, "prepare_callback", side_effect=failing):
            with self.assertRaises(ValueError):
                bridge.build_native()
        # Cache markers were not updated after the interrupted publish.
        self.assertFalse(stamp.exists())
        # The next locked build re-verifies and completes the publication.
        bridge.build_native()
        self.assertTrue(stamp.exists())
        self.assertTrue((self.root / "build/blend_callback_setup.json").is_file())

    def test_rebuilt_image_coexists_with_historical_generation_directory(self):
        # Settings drive the fingerprint away and back while nondeterministic
        # rebuilds produce different binaries, like a real toolchain does.
        bridge.build_native()
        first_generation = self.setup_metadata()["loader_fingerprint"]
        historical = self.root / "build/blend_loader" / first_generation / "loader.dll"
        historical_image = historical.read_bytes()
        self.settings["extra_option"] = 1
        bridge.build_native()
        del self.settings["extra_option"]
        bridge.build_native()
        # The fingerprint returned to its first value, but the rebuilt DLL no
        # longer matches the immutable historical copy: a distinct physical
        # key must be published instead of overwriting the old directory.
        setup = self.setup_metadata()
        self.assertTrue(setup["loader_fingerprint"].startswith(first_generation + "-"))
        self.assertEqual(historical.read_bytes(), historical_image)  # historical copy untouched
        published = self.root / "build/blend_loader" / setup["loader_fingerprint"] / "loader.dll"
        self.assertEqual(published.read_bytes(), b"loader image r3")
        self.assertEqual(
            bridge.read_json(self.root / "build/blend_loader_build.json")["generation_key"],
            setup["loader_fingerprint"],
        )
        bridge.build_native()
        self.assertEqual(self.compiles, 3)


if __name__ == "__main__":
    unittest.main()

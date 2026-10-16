import tempfile
import unittest
from pathlib import Path

from tools.generate_constants import HEADERS, PROBES, generate


class GenerateConstantsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "native").mkdir()
        self.inc = self.root / "includes"
        self.inc.mkdir()
        for header in HEADERS:
            (self.inc / header).write_text("// empty SDK fixture\n", encoding="utf-8")
        self.output = self.root / "native/constants.inc"

    def test_probe_presence_absence_and_stable_bytes(self):
        for present in (False, True, False):
            with self.subTest(present=present):
                (self.inc / "ProElemId.h").write_text(
                    "#define PRO_E_HLE_ADD_PARAMETERS 6900\n" if present else "// old SDK\n"
                )
                (self.inc / "ProHole.h").write_text(
                    "enum flag { PRO_HOLE_NO_PARAMETERS_FLAG = -1 };\n"
                    if present
                    else "// PRO_HOLE_NO_PARAMETERS_FLAG does not exist\n"
                )
                self.assertEqual(generate(self.root, inc_dir=self.inc), 2 if present else 0)
                content = self.output.read_text()
                for name in PROBES:
                    self.assertEqual(f"#define MECHDOG_HAS_{name} 1" in content, present)
                self.assertNotIn("Creo 10 SDK", content)
                self.assertNotIn(b"\r", self.output.read_bytes())
                self.output.touch()
                timestamp = self.output.stat().st_mtime_ns
                generate(self.root, inc_dir=self.inc)
                self.assertEqual(self.output.stat().st_mtime_ns, timestamp)
                macros = [line for line in content.splitlines() if line.startswith("#define")]
                self.assertEqual(macros, sorted(macros))

    def test_partial_sdk_and_commented_names_do_not_create_missing_probe(self):
        (self.inc / "ProElemId.h").write_text(
            "#define PRO_E_HLE_ADD_PARAMETERS 6900\n"
            "/* enum fake { PRO_HOLE_NO_PARAMETERS_FLAG = -1 }; */\n"
        )
        generate(self.root, inc_dir=self.inc)
        content = self.output.read_text()
        self.assertIn("#define MECHDOG_HAS_PRO_E_HLE_ADD_PARAMETERS 1", content)
        self.assertNotIn("MECHDOG_HAS_PRO_HOLE_NO_PARAMETERS_FLAG", content)

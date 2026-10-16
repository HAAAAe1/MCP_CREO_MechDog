import tempfile
import unittest
from pathlib import Path

from creo_mechdog.build_support import (
    BUILD_LOG_TAIL_BYTES,
    diagnose_build_failure,
    read_build_log_tail,
)


class BuildDiagnosticsTests(unittest.TestCase):
    def test_sdk_identifier_hint_keeps_original_error_and_ignores_warnings(self):
        error = 'geometry.cpp(104): error C2065: "PRO_E_HLE_ADD_PARAMETERS": 未声明的标识符'
        result = diagnose_build_failure(2, "warning C4819: encoding\n" + error)
        self.assertIn("SDK version hint", result)
        self.assertIn("PRO_E_HLE_ADD_PARAMETERS", result)
        self.assertIn(error, result)
        self.assertNotIn("warning C4819", result)
        self.assertEqual(diagnose_build_failure(0, error), "")

    def test_link_error_and_other_undeclared_identifier_do_not_suggest_sdk(self):
        for line in (
            "LINK : fatal error LNK1104: cannot open file kernel32.lib",
            "worker.cpp(1): error C2065: 'local_name': undeclared identifier",
            "worker.cpp(1): error C2039: 'PRO_UNKNOWN': no member",
            "PRO_SOURCE.cpp(1): error C2065: 'local_name': see PRO_OTHER documentation",
        ):
            result = diagnose_build_failure(3, line)
            self.assertIn(line, result)
            self.assertNotIn("SDK version hint", result)

    def test_summary_contains_only_last_fifteen_errors(self):
        lines = [f"worker.cpp({i}): error C2000: failure {i}" for i in range(25)]
        result = diagnose_build_failure(2, "\n".join(lines))
        self.assertEqual(result.splitlines()[1:], lines[-15:])
        self.assertIn(
            "No error-level lines", diagnose_build_failure(4, "COMPILER_PREFLIGHT: missing")
        )

    def test_log_tail_is_bounded_and_missing_log_still_has_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "build.log"
            path.write_bytes(
                b"old.cpp: error C2065: PRO_OLD\n"
                + b"x" * (BUILD_LOG_TAIL_BYTES * 2)
                + b"\nLINK : fatal error LNK1104: missing\n"
            )
            tail = read_build_log_tail(path)
            self.assertLessEqual(len(tail), BUILD_LOG_TAIL_BYTES)
            self.assertNotIn("PRO_OLD", tail)
            self.assertIn("LNK1104", diagnose_build_failure(3, tail))
            path.unlink()
            self.assertIn("could not be read", diagnose_build_failure(2, read_build_log_tail(path)))

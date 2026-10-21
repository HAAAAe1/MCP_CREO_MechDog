"""BUG-076 / FEAT-006/008: adoption budget diagnostics and refusal shaping.

Isolated, process-level cases only: the native boundary is substituted, no
Toolkit connection, build or Creo session is involved. Each case constructs an
oversized metadata file (or a native NO_CURRENT_MODEL refusal) and asserts the
structured reason code, the failing stage, the closeout behaviour and the
protection semantics. ``BUDGET_BYTES`` is shrunk for most cases so the files
stay small; one boundary case keeps the real 16 MiB budget.
"""

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

import bridge
import generic_bridge as general
from creo_mechdog import adoption
from tests.unit.test_adoption import prepare_root, synthetic_native

SMALL_BUDGET = 2048


def oversize(path: Path, budget: int, pad: int = 1) -> None:
    """Write a valid JSON document larger than ``budget`` bytes."""
    frame = len(json.dumps({"pad": ""}))
    filler = "x" * max(budget + pad - frame, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pad": filler}), encoding="utf-8")
    assert path.stat().st_size > budget


def budget_error_native(directory: Path, manifest: dict) -> dict:
    """Mirror the real worker path: dispatch began, the result file exists but
    exceeds the read budget, so the result never enters memory."""
    manifest["worker_started"] = True
    oversize(directory / "native_result.json", SMALL_BUDGET)
    raise adoption.AdoptionMetadataBudgetExceeded(
        metadata_kind="native_result",
        file=directory / "native_result.json",
        failed_stage="adopting_native_model",
        job_id=manifest.get("job_id"),
        model_id=manifest.get("model_id"),
    )


class BudgetBoundary(unittest.TestCase):
    """The read budget itself, with the real 16 MiB value."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="bug076_boundary_")
        self.file = Path(self._temporary.name) / "payload.json"
        self.addCleanup(self._temporary.cleanup)

    def test_exact_budget_passes(self):
        frame = len(json.dumps({"pad": ""}))
        filler = "x" * (adoption.BUDGET_BYTES - frame)
        self.file.write_text(json.dumps({"pad": filler}), encoding="utf-8")
        self.assertEqual(self.file.stat().st_size, adoption.BUDGET_BYTES)
        self.assertEqual(
            adoption._read(self.file, metadata_kind="x", failed_stage="y"), {"pad": filler}
        )

    def test_one_byte_over_is_structured(self):
        frame = len(json.dumps({"pad": ""}))
        filler = "x" * (adoption.BUDGET_BYTES - frame + 1)
        self.file.write_text(json.dumps({"pad": filler}), encoding="utf-8")
        with self.assertRaises(adoption.AdoptionMetadataBudgetExceeded) as caught:
            adoption._read(self.file, metadata_kind="native_result", failed_stage="s")
        payload = caught.exception.payload
        self.assertEqual(payload["reason_code"], "ADOPTION_METADATA_BUDGET_EXCEEDED")
        self.assertEqual(payload["metadata_kind"], "native_result")
        self.assertEqual(payload["actual_bytes"], self.file.stat().st_size)
        self.assertEqual(payload["budget_bytes"], 16 * 1024 * 1024)
        self.assertEqual(payload["failed_stage"], "s")
        self.assertIn("recovery", payload)
        # The tool error text is the same JSON document clients can parse.
        self.assertEqual(json.loads(str(caught.exception)), payload)

    def test_service_relative_path_falls_back_to_absolute(self):
        frame = len(json.dumps({"pad": ""}))
        filler = "x" * (adoption.BUDGET_BYTES - frame + 1)
        self.file.write_text(json.dumps({"pad": filler}), encoding="utf-8")
        with self.assertRaises(adoption.AdoptionMetadataBudgetExceeded) as caught:
            adoption._read(self.file, metadata_kind="x", failed_stage="y")
        # Outside the service root the payload reports the absolute path.
        self.assertEqual(caught.exception.payload["path"], str(self.file))


class BudgetIsolation(unittest.TestCase):
    """The four metadata kinds, closeout and protection, with a small budget."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="bug076_business_")
        self.directory = prepare_root(Path(self._temporary.name))
        real_root, real_jobs, real_models = bridge.ROOT, bridge.JOBS, general.MODELS
        bridge.ROOT = self.directory
        bridge.JOBS = self.directory / "jobs"
        general.MODELS = self.directory / "models"
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.callback(setattr, general, "MODELS", real_models)
        stack.callback(setattr, bridge, "JOBS", real_jobs)
        stack.callback(setattr, bridge, "ROOT", real_root)
        stack.callback(self._temporary.cleanup)
        stack.enter_context(
            patch.object(bridge, "build_native", return_value=self.directory / "worker.exe")
        )
        stack.enter_context(patch.object(adoption, "_native", side_effect=synthetic_native))
        stack.enter_context(patch.object(adoption, "BUDGET_BYTES", SMALL_BUDGET))

    def evidence_file(self, model_id: str, token: str) -> Path:
        return general.model_path(model_id) / "adoption" / f"evidence-{token}.json"

    def test_native_result_over_budget_reports_stage_and_cleans_staging(self):
        with patch.object(adoption, "_native", side_effect=budget_error_native):
            with self.assertRaises(adoption.AdoptionMetadataBudgetExceeded) as caught:
                adoption.inspect()
        payload = caught.exception.payload
        self.assertEqual(payload["metadata_kind"], "native_result")
        self.assertEqual(payload["failed_stage"], "adopting_native_model")
        self.assertTrue(payload["job_id"])
        # 8.3 short-path roots may fall back to the absolute path; the file name
        # itself is stable either way.
        self.assertEqual(Path(payload["path"]).name, "native_result.json")
        self.assertEqual(payload["budget_bytes"], SMALL_BUDGET)
        # The failed preflight job keeps the structured diagnosis for polling.
        probe = bridge.read_json(bridge.job_path(payload["job_id"]) / "job.json")
        self.assertEqual(probe["status"], "failed")
        self.assertEqual(probe["reason"], "ADOPTION_METADATA_BUDGET_EXCEEDED")
        self.assertEqual(probe["reason_details"]["metadata_kind"], "native_result")
        # The oversized file itself stays on disk for diagnosis.
        self.assertTrue((bridge.job_path(payload["job_id"]) / "native_result.json").is_file())
        # No staging registration survives the refusal.
        self.assertEqual(list(general.MODELS.iterdir()), [])

    def test_model_registry_over_budget_in_conflict_scan(self):
        oversize(self.directory / "models" / "ffff0000registry" / "model.json", SMALL_BUDGET)
        with self.assertRaises(adoption.AdoptionMetadataBudgetExceeded) as caught:
            adoption.inspect()
        payload = caught.exception.payload
        self.assertEqual(payload["metadata_kind"], "model_registry")
        self.assertEqual(payload["failed_stage"], "origin_conflict_scan")
        self.assertEqual(
            list(general.MODELS.glob("*/model.json")),
            [Path(self.directory / "models" / "ffff0000registry" / "model.json")],
        )

    def test_evidence_token_over_budget_at_apply(self):
        evidence = adoption.inspect()
        oversize(
            self.evidence_file(evidence["model_id"], evidence["evidence_token"]),
            SMALL_BUDGET,
        )
        with self.assertRaises(adoption.AdoptionMetadataBudgetExceeded) as caught:
            adoption.apply(evidence["model_id"], evidence["evidence_token"], None, "bug076evid1")
        self.assertEqual(caught.exception.payload["metadata_kind"], "evidence_token")
        self.assertEqual(caught.exception.payload["failed_stage"], "validate_evidence")
        self.assertEqual(caught.exception.payload["model_id"], evidence["model_id"])

    def test_apply_journal_over_budget_at_submit(self):
        evidence = adoption.inspect()
        oversize(adoption._journal(evidence["model_id"], "bug076apply1"), SMALL_BUDGET)
        with self.assertRaises(adoption.AdoptionMetadataBudgetExceeded) as caught:
            adoption.apply(evidence["model_id"], evidence["evidence_token"], None, "bug076apply1")
        self.assertEqual(caught.exception.payload["metadata_kind"], "commit_journal")
        self.assertEqual(caught.exception.payload["failed_stage"], "submit_adoption_apply")

    def test_prepare_journal_over_budget_at_submit(self):
        key = "bug076prep1"
        model_id = adoption.digest([str(general.MODELS.resolve()), "prepare", key])[:32]
        journal = general.model_path(model_id) / "adoption" / f"intent-{adoption.digest(key)}.json"
        oversize(journal, SMALL_BUDGET)
        with self.assertRaises(adoption.AdoptionMetadataBudgetExceeded) as caught:
            adoption.prepare(None, key)
        self.assertEqual(caught.exception.payload["metadata_kind"], "commit_journal")
        self.assertEqual(caught.exception.payload["failed_stage"], "submit_adoption_prepare")
        self.assertEqual(caught.exception.payload["model_id"], model_id)

    def test_native_result_over_budget_keeps_protection_and_replay_is_stable(self):
        with patch.object(adoption.subprocess, "Popen"):
            job = adoption.prepare("budget_probe", "bug076replay1")
        with patch.object(adoption, "_native", side_effect=budget_error_native):
            bridge.run_job(job["job_id"])
        result = bridge.get_job(job["job_id"], "compact")
        self.assertEqual(result["status"], "unknown_outcome")
        self.assertEqual(result["reason"], "ADOPTION_METADATA_BUDGET_EXCEEDED")
        self.assertEqual(result["reason_details"]["metadata_kind"], "native_result")
        self.assertTrue(result["recovery_required"])
        # Protection survives a budget hit: the reservation is not released.
        model = json.loads(
            (general.model_path(job["model_id"]) / "model.json").read_text(encoding="utf-8")
        )
        self.assertEqual(model["pending_job"], job["job_id"])
        # Replaying the same key returns the same protected job without rerunning.
        with patch.object(adoption, "_native", side_effect=AssertionError("no replay")):
            replay = adoption.prepare("budget_probe", "bug076replay1")
        self.assertEqual(replay["job_id"], job["job_id"])

    def test_failure_closeout_budget_hit_does_not_override_original_diagnosis(self):
        with patch.object(adoption.subprocess, "Popen"):
            job = adoption.prepare("fail_closeout", "bug076closeout1")
        # The journal is valid JSON for the direct read in _run_locked but
        # exceeds the budget for _record_failure's guarded read.
        oversize(adoption._journal(job["model_id"], "bug076closeout1"), SMALL_BUDGET)
        bridge.run_job(job["job_id"])
        result = bridge.get_job(job["job_id"], "compact")
        self.assertEqual(result["status"], "unknown_outcome")
        # The original native failure keeps its reason and message; the second
        # budget hit is only an annotation, never a replacement.
        self.assertEqual(result["reason"], "native_outcome_unconfirmed")
        self.assertIn("synthetic adoption failure", result["message"])
        self.assertNotIn("ADOPTION_METADATA_BUDGET_EXCEEDED", result["message"])
        annotation = result["failure_read_budget_exceeded"]
        self.assertEqual(annotation["metadata_kind"], "commit_journal")
        self.assertEqual(annotation["failed_stage"], "record_failure")
        # Polling after the budget hit still surfaces the recorded terminal
        # state; the journal read budget never breaks the poll itself.
        polled = bridge.get_job(job["job_id"], "compact")
        self.assertEqual(polled["status"], "unknown_outcome")
        self.assertEqual(polled["reason"], "native_outcome_unconfirmed")
        self.assertEqual(
            polled["commit_read_budget_exceeded"]["failed_stage"], "finish_adoption_commit"
        )


class NoCurrentModelRefusal(unittest.TestCase):
    """FEAT-006/008: the native empty-window prefix becomes structured."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="bug076_window_")
        self.directory = prepare_root(Path(self._temporary.name))
        real_root, real_jobs, real_models = bridge.ROOT, bridge.JOBS, general.MODELS
        bridge.ROOT = self.directory
        bridge.JOBS = self.directory / "jobs"
        general.MODELS = self.directory / "models"
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.callback(setattr, general, "MODELS", real_models)
        stack.callback(setattr, bridge, "JOBS", real_jobs)
        stack.callback(setattr, bridge, "ROOT", real_root)
        stack.callback(self._temporary.cleanup)
        stack.enter_context(
            patch.object(bridge, "build_native", return_value=self.directory / "worker.exe")
        )

    def test_no_current_model_prefix_is_structured_refusal(self):
        def empty_window(job_directory, manifest):
            raise RuntimeError(
                "NO_CURRENT_MODEL: the Creo window has no current model "
                "(ProMdlCurrentGet(&current) returned -8 PRO_TK_BAD_CONTEXT during "
                "adoption_preflight); switch to a model in Creo first; "
                "creo_list_session_models shows the session inventory"
            )

        with patch.object(adoption, "_native", side_effect=empty_window):
            refusal = adoption.inspect()
        self.assertFalse(refusal["available"])
        self.assertEqual(refusal["reason_code"], "NO_CURRENT_MODEL")
        self.assertTrue(refusal["reason"].startswith("NO_CURRENT_MODEL:"))
        self.assertIn("ProMdlCurrentGet", refusal["reason"])
        self.assertIn("-8", refusal["reason"])
        details = refusal["refusal_details"]
        self.assertFalse(details["actual_units_known"])
        self.assertEqual(details["dependency_inventory"], "unknown")
        self.assertIsNone(refusal["model_id"])
        # A structured refusal leaves no staging registration behind.
        self.assertEqual(list(general.MODELS.iterdir()), [])


class ServerBudgetContract(unittest.IsolatedAsyncioTestCase):
    """The sync tool error keeps one JSON text and structuredContent contract."""

    async def test_budget_error_returns_json_text_and_structured_content(self):
        import server

        payload = {
            "reason_code": "ADOPTION_METADATA_BUDGET_EXCEEDED",
            "metadata_kind": "native_result",
        }

        def raise_budget():
            error = adoption.AdoptionMetadataBudgetExceeded.__new__(
                adoption.AdoptionMetadataBudgetExceeded
            )
            error.payload = payload
            ValueError.__init__(error, json.dumps(payload, ensure_ascii=False))
            raise error

        result = await server.invoke(raise_budget)
        self.assertTrue(result.is_error)
        self.assertEqual(result.structured_content, payload)
        self.assertEqual(
            " ".join(block.text for block in result.content if hasattr(block, "text")),
            json.dumps(payload, ensure_ascii=False),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

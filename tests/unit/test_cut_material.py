"""BUG-054: cut results must distinguish real removal, no change and native failure."""

import subprocess
import unittest
from unittest.mock import patch

import bridge
import generic_bridge as general
from tests.unit import test_toolkit_channel as channel_tests


class CutMaterialContract(unittest.TestCase):
    setUp = channel_tests.ToolkitChannel.setUp
    submit = channel_tests.ToolkitChannel.submit

    def native_result(self, created, **result):
        model = general.model_info(created["model_id"])
        part = general.model_path(created["model_id"]) / f"output/{model['model_name']}.prt.1"
        part.write_bytes(b"synthetic native result")
        result.setdefault("part_file", str(part))
        bridge.write_json(bridge.job_path(created["job_id"]) / "native_result.json", result)
        code = 0 if result.get("success") else 1
        return subprocess.CompletedProcess("worker", code)

    def run_job(self, created, **result):
        with (
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe"),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(
                bridge.subprocess,
                "run",
                side_effect=lambda *a, **k: self.native_result(created, **result),
            ),
        ):
            bridge.run_job(created["job_id"])

    def establish_checkpoint(self):
        created = self.submit()
        self.run_job(
            created,
            success=True,
            saved_file_reloaded_and_verified=True,
            inspection={"volume_mm3": 23497.34},
            aliases={},
        )
        return created

    def test_zero_material_cut_rolls_back_and_keeps_revision(self):
        baseline = self.establish_checkpoint()
        model_id, revision = baseline["model_id"], 1
        before = general.model_info(model_id)
        self.assertEqual(before["status"], "ready")

        cut = self.submit(
            model_id=model_id,
            expected_revision=revision,
        )
        self.run_job(
            cut,
            success=False,
            saved_file_reloaded_and_verified=False,
            rollback_succeeded=True,
            inspection=None,
            message="Extrude cut removes no material; check the sketch position, "
            "direction and depth against existing geometry",
        )

        job = bridge.get_job(cut["job_id"], detail="compact")
        self.assertEqual(job["status"], "failed")
        self.assertIn("removes no material", job["message"])
        after = general.model_info(model_id)
        self.assertEqual(after["status"], "ready")
        self.assertEqual(after["revision"], revision)
        self.assertEqual(after["part_file"], before["part_file"])

    def test_successful_cut_reports_removed_material(self):
        created = self.establish_checkpoint()
        model_id = created["model_id"]
        cut = self.submit(
            model_id=model_id,
            expected_revision=1,
        )
        self.run_job(
            cut,
            success=True,
            saved_file_reloaded_and_verified=True,
            inspection={"volume_mm3": 23371.68},
            aliases={},
            operations=[
                {
                    "op": "extrude",
                    "label": "cut_in",
                    "succeeded": True,
                    "material_removed_mm3": 125.66370614359172,
                }
            ],
        )

        job = bridge.get_job(cut["job_id"], detail="full")
        self.assertEqual(job["status"], "succeeded")
        operations = job["result"]["operations"]
        self.assertEqual(operations[-1]["material_removed_mm3"], 125.66370614359172)
        self.assertEqual(general.model_info(model_id)["revision"], 2)

    def test_measurement_failure_stays_failed_without_fake_zero(self):
        created = self.establish_checkpoint()
        model_id = created["model_id"]
        cut = self.submit(
            model_id=model_id,
            expected_revision=1,
        )
        self.run_job(
            cut,
            success=False,
            saved_file_reloaded_and_verified=False,
            rollback_succeeded=False,
            toolkit_code=-1,
            message="Toolkit call ProSolidMassPropertyWithDensityGet failed with code -1",
        )

        job = bridge.get_job(cut["job_id"], detail="compact")
        self.assertEqual(job["status"], "failed")
        self.assertIn("ProSolidMassPropertyWithDensityGet", job["message"])
        model = general.model_info(model_id)
        self.assertNotEqual(model["status"], "ready")

    def test_add_mode_never_reports_removed_material(self):
        created = self.establish_checkpoint()
        model_id = created["model_id"]
        add = self.submit(
            model_id=model_id,
            expected_revision=1,
        )
        self.run_job(
            add,
            success=True,
            saved_file_reloaded_and_verified=True,
            inspection={"volume_mm3": 24497.34},
            aliases={},
            operations=[{"op": "extrude", "label": "boss", "succeeded": True}],
        )

        job = bridge.get_job(add["job_id"], detail="full")
        operations = job["result"]["operations"]
        self.assertNotIn("material_removed_mm3", operations[-1])


if __name__ == "__main__":
    unittest.main()

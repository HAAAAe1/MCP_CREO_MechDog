"""BUG-074: historical identities need reboot proof, never an unconditional escape."""

import os
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import reconciliation as rec
from tests.unit import test_reconciliation as fixtures


class LegacyRecovery(unittest.TestCase):
    setUp = fixtures.Reconciliation.setUp
    save_model = fixtures.Reconciliation.save_model
    prepare = fixtures.Reconciliation.prepare
    execute = fixtures.Reconciliation.execute
    native = fixtures.Reconciliation.native

    def legacy(self):
        directory = bridge.job_path(self.original)
        job = bridge.read_json(directory / "job.json")
        job.pop("runner_identity")
        bridge.write_json(directory / "job.json", job)
        (directory / "native_owner.json").unlink()
        return directory

    def boot(self, delta=60):
        # Synthetic boot is later than fixture creation; no actual restart or native work.
        stamp = time.time() + delta
        return {
            "started_at": datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
            "time_ns": int(stamp * 1e9),
            "source": "isolated cross-checked boot fixture",
        }

    def test_previous_boot_unlocks_only_owner_gate_for_all_four_actions(self):
        self.legacy()
        with patch.object(rec, "boot_info", return_value=self.boot()):
            snapshot = rec._snapshot(self.mid)
        self.assertTrue(snapshot["owners"][0]["stopped"])
        live = {
            "loaded": True,
            "owned": True,
            "inspection": self.state,
            "millimeter_units": True,
            "dependency_free": True,
        }
        snapshot["candidate"] = {"identity": {"path": "different saved candidate"}}
        self.assertTrue(rec._actions(snapshot, live)["restore_baseline"]["available"])
        self.assertTrue(rec._actions(snapshot, live)["accept_saved"]["available"])
        self.assertTrue(rec._actions(snapshot, live)["accept_live"]["available"])
        self.assertFalse(rec._actions(snapshot, live)["abandon_new"]["available"])
        snapshot["model"] = {**snapshot["model"], "part_file": None, "revision": 0}
        self.assertTrue(rec._actions(snapshot, live)["abandon_new"]["available"])

    def test_same_boot_and_unavailable_boot_keep_all_actions_unavailable(self):
        self.legacy()
        for boot in (None, self.boot(-60)):
            with self.subTest(boot=boot), patch.object(rec, "boot_info", return_value=boot):
                result = rec.inspect(self.mid)
                self.assertTrue(all(not a["available"] for a in result["actions"].values()))
                self.assertIn("guidance", result["owners"][0])

    def test_known_active_or_permission_unknown_owner_never_uses_reboot_fallback(self):
        for alive in (True, None):
            with (
                self.subTest(alive=alive),
                patch.object(rec, "process_identity", return_value={"alive": alive, "created": 12}),
                patch.object(rec, "boot_info") as query,
            ):
                self.assertFalse(rec._snapshot(self.mid)["owners"][0]["stopped"])
                query.assert_not_called()

    def test_missing_record_and_current_declared_time_refuse(self):
        directory = self.legacy()
        with patch.object(rec, "boot_info", return_value=self.boot()):
            job = bridge.read_json(directory / "job.json")
            job["finished_at"] = datetime.fromtimestamp(time.time() + 120, timezone.utc).isoformat()
            bridge.write_json(directory / "job.json", job)
            self.assertFalse(rec._snapshot(self.mid)["owners"][0]["stopped"])
            (directory / "request.json").unlink()
            with self.assertRaises(ValueError):
                rec.inspect(self.mid)

    def test_timestamp_only_change_expires_token_and_does_not_touch_model(self):
        directory = self.legacy()
        with patch.object(rec, "boot_info", return_value=self.boot()):
            evidence = rec.inspect(self.mid)
            target = directory / "request.json"
            stat = target.stat()
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
            before = (general.model_path(self.mid) / "model.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "Stale evidence"):
                rec.apply(
                    self.mid,
                    "restore_baseline",
                    1,
                    self.original,
                    evidence["evidence_token"],
                    "legacy_touch_refusal",
                )
            self.assertEqual(before, (general.model_path(self.mid) / "model.json").read_bytes())

    def test_restore_commits_once_and_retains_original_job_with_reboot_evidence(self):
        directory = self.legacy()
        before = (directory / "job.json").read_bytes()
        with patch.object(rec, "boot_info", return_value=self.boot()):
            created, args = self.prepare(key="legacy_restore_once")
            result = self.execute(created)
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(rec.apply(*args)["job_id"], created["job_id"])
        self.assertEqual(before, (directory / "job.json").read_bytes())
        self.assertEqual(general.model_info(self.mid)["revision"], 1)

    def test_reboot_evidence_change_after_admission_refuses_before_native(self):
        directory = self.legacy()
        with patch.object(rec, "boot_info", return_value=self.boot()):
            created, _ = self.prepare(key="legacy_changed_after_admission")
            target = directory / "request.json"
            stat = target.stat()
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
            with patch.object(rec, "_native") as worker:
                bridge.run_job(created["job_id"])
            worker.assert_not_called()
        result = bridge.get_job(created["job_id"], "compact")
        self.assertEqual(result["failure_phase"], "before_native")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["recovery_pending_released"])
        self.assertEqual(general.model_info(self.mid)["pending_job"], self.original)

    def test_legacy_abandon_still_preserves_files_and_refuses_later_edits(self):
        self.legacy()
        with patch.object(rec, "boot_info", return_value=self.boot()):
            fixtures.Reconciliation.test_abandon_preserves_files_and_prevents_ordinary_edit(self)

    def test_legacy_accept_live_increments_only_once(self):
        self.legacy()
        with patch.object(rec, "boot_info", return_value=self.boot()):
            fixtures.Reconciliation.test_live_requires_explicit_preflight_and_increments_once(self)

    def test_legacy_accept_saved_keeps_baseline_and_advances_revision_once(self):
        directory = self.legacy()
        baseline = self.part
        candidate = baseline.with_name("owned_part.prt.3")
        candidate.write_bytes(b"verified candidate fixture")
        bridge.write_json(
            directory / "native_result.json",
            {
                "success": True,
                "saved_file_reloaded_and_verified": True,
                "part_file": str(candidate),
                "inspection": self.state,
                "aliases": {},
            },
        )
        self.part = candidate
        with patch.object(rec, "boot_info", return_value=self.boot()):
            created, args = self.prepare(action="accept_saved", key="legacy_accept_saved")
            result = self.execute(created)
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(rec.apply(*args)["job_id"], created["job_id"])
        self.assertTrue(baseline.exists())
        self.assertEqual(general.model_info(self.mid)["revision"], 2)

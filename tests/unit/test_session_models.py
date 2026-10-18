"""Session discovery contracts; native calls are substituted, never connect Creo."""

import hashlib
import json
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import session_models as inventory
from creo_mechdog.model_queries import decode_cursor, encode_cursor
from tests.unit import test_adoption as fixture


def synthetic_inventory(directory, manifest):
    return {
        "session_fingerprint": "fixture-session-inventory",
        "complete": True,
        "type_errors": [],
        "truncated": False,
        "models": [
            {
                "name": "001",
                "model_type": "part",
                "is_current": True,
                "origin": "",
                "has_saved_origin": False,
                "modified": True,
                "session_model_id": 10,
            },
            {
                "name": "saved",
                "model_type": "sheetmetal",
                "is_current": False,
                "origin": str(bridge.ROOT / "user_parts" / "001.prt"),
                "has_saved_origin": True,
                "modified": False,
                "session_model_id": 11,
            },
            {
                "name": None,
                "model_type": "assembly",
                "is_current": False,
                "origin": None,
                "has_saved_origin": None,
                "modified": None,
                "session_model_id": None,
                "query_codes": {"origin": -1},
            },
        ],
    }


class SessionInventoryRules(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="session_models_")
        self.addCleanup(temporary.cleanup)
        self.directory = fixture.prepare_root(Path(temporary.name))
        stack = ExitStack()
        self.addCleanup(stack.close)
        for obj, name, value in (
            (bridge, "ROOT", self.directory),
            (bridge, "JOBS", self.directory / "jobs"),
            (general, "MODELS", self.directory / "models"),
        ):
            stack.enter_context(patch.object(obj, name, value))
        self.native = stack.enter_context(
            patch.object(inventory, "_probe", side_effect=synthetic_inventory)
        )

    def test_frozen_pages_use_one_probe_and_preserve_unknowns(self):
        first = inventory.list_session_models(1)
        self.assertTrue(first["models"][0]["is_current"])
        self.assertFalse(first["models"][0]["has_saved_origin"])
        second = inventory.list_session_models(1, first["next_cursor"])
        third = inventory.list_session_models(1, second["next_cursor"])
        self.assertIsNone(third["models"][0]["origin"])
        self.assertIsNone(third["models"][0]["modified"])
        self.assertEqual(first["snapshot_id"], third["snapshot_id"])
        self.assertIsNone(third["next_cursor"])
        self.assertEqual(self.native.call_count, 1)
        self.assertEqual(list(general.MODELS.iterdir()), [])

    def test_invalid_expired_changed_and_wrong_selection_cursors(self):
        for value in (0, 51, True):
            with self.assertRaises(ValueError):
                inventory.list_session_models(value)
        with self.assertRaises(ValueError):
            inventory.list_session_models(cursor="not a cursor")
        first = inventory.list_session_models(1)
        cursor = first["next_cursor"]
        file = bridge.job_path(first["snapshot_id"]) / "session_models.json"
        snapshot = bridge.read_json(file)
        with patch.object(inventory.time, "time", return_value=time.time() + 601):
            with self.assertRaisesRegex(ValueError, "expired"):
                inventory.list_session_models(1, cursor)
        with patch.object(inventory, "_selection", return_value="another-selection"):
            with self.assertRaisesRegex(ValueError, "selection changed"):
                inventory.list_session_models(1, cursor)
        snapshot["models"][0]["name"] = "changed snapshot"
        bridge.write_json(file, snapshot)
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            inventory.list_session_models(1, cursor)
        wrong = decode_cursor(cursor)
        wrong["kind"] = "models"
        with self.assertRaises(ValueError):
            inventory.list_session_models(1, encode_cursor(wrong))

    def test_association_requires_owned_path_and_matching_hash_not_name(self):
        mid = "a" * 32
        output = general.model_path(mid) / "output"
        output.mkdir(parents=True)
        file = output / "saved.prt.1"
        file.write_bytes(b"verified saved part")
        bridge.write_json(
            output.parent / "model.json",
            {
                "model_id": mid,
                "model_name": "saved",
                "model_type": "part",
                "status": "ready",
                "output_directory": str(output),
                "part_file": str(file),
                "part_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            },
        )
        records = [
            {"name": "different_display_name", "origin": str(file)},
            {"name": "saved", "origin": ""},
        ]
        inventory._associations(records)
        self.assertEqual(records[0]["model_id"], mid)
        self.assertIsNone(records[1]["model_id"])
        file.write_bytes(b"changed native file")
        inventory._associations(records)
        self.assertIsNone(records[0]["model_id"])

    def test_utf8_page_budget_reports_continuation(self):
        def many(directory, manifest):
            result = synthetic_inventory(directory, manifest)
            result["models"] = [{"name": "模型" * 200, "origin": None} for _ in range(50)]
            return result

        self.native.side_effect = many
        result = inventory.list_session_models(50)
        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False).encode()), inventory.PAGE_BYTES
        )
        self.assertLess(len(result["models"]), 50)
        self.assertIsNotNone(result["next_cursor"])

    def test_busy_and_native_failure_do_not_create_models(self):
        with patch.object(bridge, "toolkit_lock", side_effect=bridge.ToolkitBusy("fixture busy")):
            with self.assertRaises(bridge.ToolkitBusy):
                inventory.list_session_models()
        self.assertEqual(list(bridge.JOBS.iterdir()), [])
        self.native.side_effect = RuntimeError("synthetic native query failure")
        with self.assertRaisesRegex(RuntimeError, "query failure"):
            inventory.list_session_models()
        self.assertEqual(list(general.MODELS.iterdir()), [])
        job = next(bridge.JOBS.glob("*/job.json"))
        self.assertEqual(bridge.read_json(job)["status"], "failed")


class SessionInventoryMcp(unittest.IsolatedAsyncioTestCase):
    client = fixture.AdoptionMcpContract.client
    call = fixture.AdoptionMcpContract.call

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="session_models_stdio_")
        cls.directory = fixture.prepare_root(Path(cls.temporary.name))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    async def test_real_stdio_schema_pagination_nulls_and_validation(self):
        async with self.client() as client:
            tools = await client.list_tools()
            tool = next(t for t in tools.tools if t.name == "creo_list_session_models")
            self.assertTrue(tool.annotations.read_only_hint)
            first = await self.call(client, "creo_list_session_models", {"limit": 2})
            second = await self.call(
                client, "creo_list_session_models", {"limit": 2, "cursor": first["next_cursor"]}
            )
            self.assertEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertIsNone(second["models"][0]["origin"])
            reply = await client.call_tool("creo_list_session_models", {"limit": 51})
            self.assertTrue(reply.is_error)
            reply = await client.call_tool("creo_list_session_models", {"cursor": "broken"})
            self.assertTrue(reply.is_error)

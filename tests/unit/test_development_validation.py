"""DEV-002 pure validation and modeling-helper regressions."""

import unittest

from creo_mechdog.schema import validate_operations


class DevelopmentValidation(unittest.TestCase):
    def test_invalid_table_shapes_and_updates(self):
        for op in [
            {
                "op": "drawing_table",
                "label": "t",
                "position": [0, 0],
                "columns": [20, 30],
                "cells": [["only one"]],
            },
            {"op": "drawing_table_cell", "table": "t", "row": 0, "column": 1, "text": "bad"},
            {"op": "drawing_view_update", "view": "front"},
            {"op": "drawing_note_update", "note": "n"},
        ]:
            with self.subTest(op=op), self.assertRaises(ValueError):
                validate_operations([op])

    def test_boolean_distinct_bodies_and_counts(self):
        op = {
            "op": "boolean_bodies",
            "label": "b",
            "method": "union",
            "targets": [{"kind": "body", "id": 1}],
            "tools": [{"kind": "body", "id": 2}],
        }
        validate_operations([op])
        for changes in [
            {"tools": [{"kind": "body", "id": 1}]},
            {"keep_tools": True},
            {"targets": [{"kind": "body", "id": 1}, {"kind": "body", "id": 3}]},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_operations([{**op, **changes}])

    def test_datum_and_surface_parameters(self):
        for op in [
            {"op": "datum_csys", "label": "c", "translation": [1, 2]},
            {
                "op": "datum_points",
                "label": "p",
                "points": [
                    {"name": "a", "position": [0, 0, 0]},
                    {"name": "a", "position": [1, 2, 3]},
                ],
            },
            {
                "op": "thicken",
                "label": "t",
                "reference": {"kind": "quilt", "id": 1},
                "thickness": 0,
            },
        ]:
            with self.subTest(op=op), self.assertRaises(ValueError):
                validate_operations([op])


if __name__ == "__main__":
    unittest.main()

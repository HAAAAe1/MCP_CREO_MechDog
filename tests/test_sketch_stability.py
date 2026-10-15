"""Reject malformed profiles without ruling out valid complex or open sketches."""

import unittest
from unittest.mock import patch

import generic_bridge
from creo_mechdog.profile_checks import closed_profile
from creo_mechdog.schema import validate_operations


class SketchStability(unittest.TestCase):
    def test_arc_capsule_closes_in_arbitrary_entity_order(self):
        entities = [
            {
                "type": "arc",
                "name": "right",
                "center": [10, 0],
                "radius": 5,
                "start_angle": -90,
                "end_angle": 90,
            },
            {"type": "line", "name": "top", "start": [-10, 5], "end": [10, 5]},
            {
                "type": "arc",
                "name": "left",
                "center": [-10, 0],
                "radius": 5,
                "start_angle": 90,
                "end_angle": 270,
            },
            {"type": "line", "name": "bottom", "start": [10, -5], "end": [-10, -5]},
        ]
        self.assertEqual(closed_profile(entities)["closed_contour_count"], 1)

    def test_open_report_fragment_rejected_before_queue(self):
        entities = [
            {"type": "line", "name": "d1", "start": [0, -6800], "end": [0, 6800]},
            {"type": "line", "name": "d2", "start": [0, 6900], "end": [68300, 6900]},
            {
                "type": "arc",
                "name": "d3",
                "center": [68300, -9176.0869],
                "radius": 16076.0869,
                "start_angle": 34.8054,
                "end_angle": 90,
            },
            {"type": "line", "name": "d5", "start": [68300, -6900], "end": [0, -6900]},
        ]
        sections = [
            dict(op="sketch", label=f"s{i}", entities=entities, offset=i * 1000) for i in range(2)
        ]
        with patch.object(generic_bridge, "submit") as submit:
            with self.assertRaisesRegex(ValueError, "open or branched"):
                generic_bridge.new_loft_part(None, None, sections)
            submit.assert_not_called()

    def test_open_sketch_allowed_but_not_a_solid_blend_contour(self):
        entities = [dict(type="line", name="rail", start=[0, 0], end=[40, 0])]
        validate_operations([dict(op="sketch", label="path", entities=entities)])
        with self.assertRaises(ValueError):
            closed_profile(entities)

    def test_multiple_loops_and_branches_rejected(self):
        circle = dict(type="circle", name="a", center=[0, 0], radius=10)
        with self.assertRaises(ValueError):
            closed_profile([circle, {**circle, "name": "b", "center": [40, 0]}])
        rect = dict(type="rectangle", name="r", min=[0, 0], max=[10, 10])
        with self.assertRaises(ValueError):
            closed_profile([rect, dict(type="line", name="spur", start=[0, 0], end=[-5, 0])])

    def test_unverified_solver_paths_rejected_and_degenerate_input(self):
        sketch = dict(
            op="sketch",
            label="s",
            entities=[dict(type="circle", name="c", center=[0, 0], radius=10)],
        )
        for solver in ("auto", "rigid", "explicit"):
            with self.assertRaises(ValueError):
                validate_operations([{**sketch, "solver": solver}])
        with self.assertRaises(ValueError):
            validate_operations([{**sketch, "normalize": True}])
        with self.assertRaises(ValueError):
            validate_operations([{**sketch, "deny_inferred_constraints": True}])
        for entity in [
            dict(type="arc", name="a", center=[0, 0], radius=10, start_angle=0, end_angle=360),
            dict(type="polyline", name="p", points=[[0, 0], [0, 0], [10, 0]]),
        ]:
            with self.assertRaises(ValueError):
                validate_operations([{**sketch, "entities": [entity]}])

    def test_coordinate_mode_scope_and_mixed_dimensions_rejected_before_queue(self):
        sketch = dict(
            op="sketch",
            label="s",
            dimensioning="coordinates",
            entities=[
                dict(
                    type="arc", name="a", center=[0, 0], radius=5000, start_angle=-90, end_angle=90
                )
            ],
        )
        self.assertEqual(validate_operations([sketch])[0]["dimensioning"], "coordinates")
        for change in (
            {"dimensioning": "rigid"},
            {"plane": {"reference": {"kind": "surface", "id": 1}}},
            {"entities": [dict(type="spline", name="s", points=[[0, 0], [10, 5], [20, 0]])]},
            {"dimensions": [dict(name="r", type="radius", refs=[{"entity": "a"}], value=5000)]},
            {"constraints": [dict(type="horizontal", refs=[{"entity": "a"}])]},
        ):
            with patch.object(generic_bridge.bridge, "toolkit_lock") as lock:
                with self.assertRaises(ValueError):
                    generic_bridge.submit([{**sketch, **change}])
                lock.assert_not_called()

    def test_coordinate_geometry_edit_schema_and_automatic_compatibility(self):
        entities = [dict(type="rectangle", name="box", min=[-5000, -1000], max=[5000, 1000])]
        ops = validate_operations(
            [
                dict(
                    op="update_sketch_geometry",
                    sketch="s",
                    entities=entities,
                    dimensioning="coordinates",
                )
            ]
        )
        self.assertEqual(ops[0]["dimensioning"], "coordinates")
        auto = validate_operations([dict(op="sketch", label="s", entities=entities)])
        self.assertEqual(auto[0]["dimensioning"], "auto")
        for mode in ("auto", "autodim", "coordinates"):
            validate_operations(
                [dict(op="sketch", label="s", entities=entities, dimensioning=mode)]
            )


if __name__ == "__main__":
    unittest.main()

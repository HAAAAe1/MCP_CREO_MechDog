"""DEV-002 pure validation and modeling-helper regressions."""

import unittest

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

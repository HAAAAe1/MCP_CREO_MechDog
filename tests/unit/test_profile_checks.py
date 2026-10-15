"""DEV-002 preserve closure tolerance and degenerate contour rejection."""

import unittest

from creo_mechdog.profile_checks import closed_profile


class ProfileChecksTests(unittest.TestCase):
    def contour(self, gap):
        return [
            {"type": "line", "start": [0, 0], "end": [10, 0]},
            {"type": "line", "start": [10, 0], "end": [10, 10]},
            {"type": "line", "start": [10, 10], "end": [0, 10]},
            {"type": "line", "start": [0, 10], "end": [0, gap]},
        ]

    def test_closure_tolerance_boundary_and_custom_tolerance(self):
        self.assertEqual(
            closed_profile(self.contour(0.0001)),
            {"closed_contour_count": 1, "closure_tolerance_mm": 0.0001},
        )
        with self.assertRaisesRegex(ValueError, "open or branched"):
            closed_profile(self.contour(0.0001001))
        self.assertEqual(
            closed_profile(self.contour(0.001), tolerance=0.001)["closed_contour_count"], 1
        )

    def test_short_edges_rejected_before_topology_is_accepted(self):
        with self.assertRaisesRegex(ValueError, "edge shorter than the closure tolerance"):
            closed_profile([{"type": "line", "start": [0, 0], "end": [0, 0.0001]}])

    def test_construction_geometry_does_not_add_contours(self):
        construction = [
            {"type": "circle", "center": [50, 50], "radius": 3, "construction": True},
            {"type": "centerline", "start": [-10, 0], "end": [10, 0]},
        ]
        self.assertEqual(closed_profile(self.contour(0) + construction)["closed_contour_count"], 1)


if __name__ == "__main__":
    unittest.main()

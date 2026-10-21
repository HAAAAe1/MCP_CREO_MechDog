"""BUG-058: describe visible, hidden, missing and unreadable windows without killing."""

import unittest
from unittest.mock import patch

from creo_mechdog import window_observations as windows


class WindowObservations(unittest.TestCase):
    def test_window_states_and_unresponsive_observations_are_separate(self):
        with patch.object(
            windows,
            "_enumerate_windows",
            return_value=[(10, True, False), (10, False, False), (11, False, True)],
        ):
            result = windows.window_observations({10, 11, 12})
        self.assertEqual(result[10]["state"], "visible")
        self.assertEqual(result[10]["top_level_count"], 2)
        self.assertEqual(result[11]["state"], "hidden_only")
        self.assertTrue(result[11]["hung_window_observed"])
        self.assertEqual(result[12]["state"], "none_observed")

    def test_access_failure_is_unknown_not_no_window(self):
        with patch.object(windows, "_enumerate_windows", side_effect=OSError("denied")):
            self.assertEqual(windows.window_observations({10})[10]["state"], "unknown")

    def test_guidance_never_infers_death_from_window_absence(self):
        snapshot = {"processes": [{"matches": True, "windows": {"state": "none_observed"}}]}
        text = windows.connection_guidance(snapshot)
        self.assertIn("does not prove", text)
        self.assertIn("does not authorize", text)
        snapshot["processes"][0]["windows"]["state"] = "visible"
        self.assertIn("Dashboard", windows.connection_guidance(snapshot))
        snapshot["processes"][0]["matches"] = False
        self.assertIn("unconfirmed", windows.connection_guidance(snapshot))

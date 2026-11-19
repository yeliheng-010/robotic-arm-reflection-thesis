import unittest
from cv_policy import frame_gate, REQUIRED


class SlenderTests(unittest.TestCase):
    def rows(self):
        return {n: dict(pixels=900, isolated_pixels=1000, short_side=25,
                       long_side=40, largest_component=900, framed=True) for n in REQUIRED}

    def test_clear_slender_tool_is_not_rejected_for_being_thin(self):
        rows = self.rows()
        rows['Flashlight'].update(pixels=350, isolated_pixels=355, short_side=14,
                                  long_side=32, largest_component=350)
        self.assertTrue(frame_gate(rows)['passed'])

    def test_occluded_slender_tool_still_fails(self):
        rows = self.rows()
        rows['Flashlight'].update(pixels=350, isolated_pixels=500, short_side=14,
                                  long_side=32, largest_component=350)
        self.assertFalse(frame_gate(rows)['passed'])

    def test_small_round_top_of_tool_is_insufficient(self):
        rows = self.rows()
        rows['Flashlight'].update(pixels=300, isolated_pixels=300, short_side=20,
                                  long_side=22, largest_component=300)
        self.assertFalse(frame_gate(rows)['passed'])

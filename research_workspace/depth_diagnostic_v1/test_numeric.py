import unittest
import numpy as np
from depth_diagnostic_v1.numeric import samples, summary


class NumericTests(unittest.TestCase):
    def test_original_six_mm_gate_is_preserved(self):
        self.assertTrue(summary([dict(outside_m=.006)])['passed'])
        self.assertFalse(summary([dict(outside_m=.006001)])['passed'])

    def test_empty_mask_is_not_calibrated(self):
        rows = samples(np.ones((8, 8)), np.zeros((8, 8)), transform=np.eye(4),
            intrinsics=[100, 100, 4, 4], box=[[-1, -1, 0], [1, 1, 2]], kernel=3)
        self.assertEqual([], rows)
        self.assertFalse(summary(rows)['passed'])

    def test_world_coordinates_find_known_outside_depth(self):
        rows = samples(np.ones((8, 8)), np.ones((8, 8)), transform=np.eye(4),
            intrinsics=[100, 100, 4, 4], box=[[-1, -1, 0], [1, 1, .98]], kernel=3)
        self.assertAlmostEqual(.02, summary(rows)['max_outside_bounds_m'])
        self.assertFalse(summary(rows)['passed'])


if __name__ == '__main__':
    unittest.main()

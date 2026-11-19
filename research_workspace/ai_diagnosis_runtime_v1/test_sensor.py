import unittest
import numpy as np
from sensor_math import surface, uniform_rows


class SensorTests(unittest.TestCase):
    def test_depth_change_changes_position_without_truth_input(self):
        mask = np.ones((8, 8), dtype=bool)
        args = dict(transform=np.eye(4), intrinsics=(10., 10., 4., 4.))
        a = surface(np.ones((8, 8)), mask, **args)
        b = surface(np.full((8, 8), 2.), mask, **args)
        self.assertEqual(1., a['surface_centroid_world_m'][2])
        self.assertEqual(2., b['surface_centroid_world_m'][2])

    def test_no_depth_is_unknown_not_filled_with_truth(self):
        row = surface(np.zeros((8, 8)), np.ones((8, 8), dtype=bool),
                      transform=np.eye(4), intrinsics=(10., 10., 4., 4.))
        self.assertIsNone(row['surface_centroid_world_m'])
        self.assertEqual('insufficient_visible_depth', row['status'])

    def test_invalid_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            surface(np.zeros((8, 8)), np.ones((8, 7), dtype=bool),
                    transform=np.eye(4), intrinsics=(10., 10., 4., 4.))

    def test_telemetry_summary_uses_uniform_indices(self):
        rows = [{'time_s': i, 'q_rad': [i]*6} for i in range(100)]
        chosen = uniform_rows(rows, limit=4)
        self.assertEqual([0, 33, 66, 99], [r['time_s'] for r in chosen])


if __name__ == '__main__':
    unittest.main()

import copy
import unittest
import numpy as np
from geometry_v3 import reconstructed_placement


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.geometry = dict(source_center=[0., 0., .1], source_half=[.02, .02, .02],
            bin_center=[0., 0., 0.], interior_half=[.2, .2], usable_half=[.16, .16], wall_top=.1)
        pose = np.eye(4)
        pose[:3, 3] = [0., 0., .1]
        self.row = dict(target=[0., 0., .13], pose=pose.tolist(), goal=dict(bottom_gap=.01))

    def test_opposing_submicron_errors_propagate(self):
        current = copy.deepcopy(self.geometry)
        current['source_center'][2] -= .8e-6
        current['source_half'][2] += .8e-6
        out = reconstructed_placement(self.row, self.geometry, current=current)
        self.assertAlmostEqual(-1.6e-6, out['gap_reconstruction_delta_m'])

    def test_per_field_limit_unchanged(self):
        current = copy.deepcopy(self.geometry)
        current['source_center'][2] += 1.1e-6
        with self.assertRaises(AssertionError):
            reconstructed_placement(self.row, self.geometry, current=current)

    def test_tampered_cached_gap_rejected(self):
        row = dict(self.row, goal=dict(bottom_gap=.011))
        with self.assertRaises(AssertionError):
            reconstructed_placement(row, self.geometry, current=self.geometry)

    def test_static_geometry_change_rejected(self):
        current = dict(self.geometry, wall_top=.1000001)
        with self.assertRaises(AssertionError):
            reconstructed_placement(self.row, self.geometry, current=current)

    def test_outside_and_nonpositive_gap_rejected(self):
        for target, gap in [([.3, 0., .13], .01), ([0., 0., .11], -.01)]:
            row = dict(self.row, target=target, goal=dict(bottom_gap=gap))
            with self.assertRaises(AssertionError):
                reconstructed_placement(row, self.geometry, current=self.geometry)


if __name__ == '__main__':
    unittest.main()

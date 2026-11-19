"""只对缺失且有可靠局部支持的目标内部像素补值。"""
import copy
import math
import unittest
from depth_estimate import estimate


def fixture():
    depth = [[1.0 for _ in range(7)] for _ in range(7)]
    mask = [[True for _ in range(7)] for _ in range(7)]
    depth[3][3] = 0
    return depth, mask


class DepthTests(unittest.TestCase):
    def test_local_recovery_preserves_input_and_noise_values(self):
        depth, mask = fixture()
        depth[2][2] = 1.006
        depth[2][4] = .994
        original = copy.deepcopy(depth)
        row = estimate(depth, mask, pixel=(3, 3))
        self.assertTrue(row['accepted'])
        self.assertEqual(1., row['value_m'])
        self.assertEqual(original, depth)

    def test_valid_pixel_is_noop(self):
        depth, mask = fixture()
        depth[3][3] = 1.006
        self.assertFalse(estimate(depth, mask, pixel=(3, 3))['accepted'])
        self.assertEqual(1.006, depth[3][3])

    def test_target_edge_and_other_object_are_rejected(self):
        depth, mask = fixture()
        mask[3][3] = False
        self.assertFalse(estimate(depth, mask, pixel=(3, 3))['accepted'])
        mask[3][3], mask[2][3] = True, False
        self.assertFalse(estimate(depth, mask, pixel=(3, 3))['accepted'])

    def test_sparse_or_one_sided_support_rejected(self):
        depth, mask = fixture()
        for v in range(1, 6):
            for u in range(1, 6):
                depth[v][u] = 1. if v < 3 else 0
        self.assertFalse(estimate(depth, mask, pixel=(3, 3))['accepted'])

    def test_depth_discontinuity_rejected(self):
        depth, mask = fixture()
        for v in range(1, 6):
            depth[v][1] = 1.1
            depth[v][2] = 1.1
        self.assertFalse(estimate(depth, mask, pixel=(3, 3))['accepted'])

    def test_nan_center_can_recover_but_invalid_support_is_ignored(self):
        depth, mask = fixture()
        depth[3][3], depth[1][1] = math.nan, math.inf
        self.assertTrue(estimate(depth, mask, pixel=(3, 3))['accepted'])

    def test_coordinates_outside_image_and_border_are_rejected(self):
        depth, mask = fixture()
        for pixel in ((-1, 3), (7, 3), (0, 0), (math.nan, 3), (True, 3)):
            self.assertFalse(estimate(depth, mask, pixel=pixel)['accepted'])


if __name__ == '__main__':
    unittest.main()

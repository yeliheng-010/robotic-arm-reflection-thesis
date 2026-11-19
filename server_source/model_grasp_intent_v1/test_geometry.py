import unittest
import numpy as np
from model_grasp_intent_v1.geometry import propose
from model_grasp_intent_v1.test_contract import intent


def points():
    x, y = np.meshgrid(np.linspace(-.06, .06, 41), np.linspace(-.015, .015, 21))
    return np.column_stack((x.ravel()+.8, y.ravel()+.4, np.full(x.size, .79)))


class GeometryTests(unittest.TestCase):
    def test_top_coordinates_match_existing_convention(self):
        result = propose(points(), [.8, .4, .76], intent())
        self.assertEqual('proposal', result['status'])
        pose = np.asarray(result['pose'])
        np.testing.assert_allclose([0, 0, -1], pose[:3, 0], atol=1e-12)
        np.testing.assert_allclose([.8, .4, .76], pose[:3, 3], atol=1e-12)
        self.assertFalse(result['full_path_verified'])

    def test_shift_depth_and_tilt_have_separate_effects(self):
        first = propose(points(), [.8, .4, .76], intent())
        next_pose = propose(points(), [.8, .4, .76],
                            intent(region='long_positive', depth_mm=15, tilt_deg=60))
        first, second = np.asarray(first['pose']), np.asarray(next_pose['pose'])
        self.assertAlmostEqual(.02, np.linalg.norm(second[:2, 3]-first[:2, 3]))
        self.assertAlmostEqual(.775, second[2, 3])
        np.testing.assert_allclose(np.eye(3), second[:3, :3].T@second[:3, :3], atol=1e-12)
        self.assertAlmostEqual(1, np.linalg.det(second[:3, :3]))
        self.assertAlmostEqual(-.5, second[2, 0])

    def test_nominal_distance_is_not_relaxed(self):
        result = propose(points(), [.9, .4, .76], intent())
        self.assertEqual('rejected', result['status'])
        self.assertEqual('translation_limit', result['reason'])

    def test_side_approach_parallel_to_closing_axis_rejected(self):
        result = propose(points(), [.8, .4, .76], intent(tilt_deg=90, azimuth_deg=90))
        self.assertEqual('degenerate_closing_axis', result['reason'])

    def test_observed_width_guard_retained(self):
        cloud = points()
        cloud[:, 1] = .4 + 4*(cloud[:, 1]-.4)
        result = propose(cloud, [.8, .4, .76], intent())
        self.assertEqual('observed_span', result['reason'])

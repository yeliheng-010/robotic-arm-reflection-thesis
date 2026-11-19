import unittest
import numpy as np
from top_fit import estimate


def fixture():
    rng = np.random.default_rng(42)
    angle = np.deg2rad(24)
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    top = rng.uniform([-.031,-.038], [.031,.038], (4000,2))@rotation.T+[1.,.1]
    top = np.column_stack((top, np.full(len(top), .816)))
    side = rng.uniform([-.031,.038,.74], [.031,.038,.81], (5000,3))
    side[:,:2] = side[:,:2]@rotation.T+[1.,.1]
    return np.concatenate((top,side))+rng.normal(0,.003,(9000,3)), rotation[:,0]


class TopFitTests(unittest.TestCase):
    def test_noisy_rotated_box_with_dominant_side(self):
        points, axis = fixture()
        result = estimate(points)
        self.assertTrue(result['available'])
        self.assertLess(np.linalg.norm(np.array(result['center'])[:2]-[1.,.1]), .006)
        self.assertGreater(abs(np.dot(axis, result['closing_axis'][:2])), .97)
        self.assertAlmostEqual(.786, result['center'][2], delta=.008)
        self.assertGreater(result['width_m'], .05)
        self.assertLess(result['width_m'], .075)

    def test_insufficient_and_invalid_observations(self):
        self.assertFalse(estimate(np.zeros((30,3)))['available'])
        self.assertFalse(estimate(np.full((100,3), np.nan))['available'])
        self.assertFalse(estimate(np.zeros((100,3)))['available'])

    def test_permutation_and_translation(self):
        points, _ = fixture()
        first = estimate(points)
        second = estimate(points[::-1]+[.2,-.1,.04])
        np.testing.assert_allclose(np.array(first['center'])+[.2,-.1,.04], second['center'], atol=1e-10)
        self.assertAlmostEqual(first['width_m'], second['width_m'])


if __name__ == '__main__':
    unittest.main()

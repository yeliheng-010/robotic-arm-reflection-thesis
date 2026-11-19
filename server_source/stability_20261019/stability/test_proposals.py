from pathlib import Path
import unittest
import numpy as np
from geometry.candidates import original
from stability.detector import StableDetector
from stability.proposals import generate, filter_then_nms

ROOT = Path('/home/yeliheng/grasp_server/geometry_20261019')


class ProposalTests(unittest.TestCase):
    def test_offsets_are_bounded_and_original_is_retained(self):
        points = np.load(ROOT/'OrangeSphere-none.npz')['target']
        group = generate(points)
        np.testing.assert_array_equal(original(points).grasp_group_array[0], group.grasp_group_array[0])
        delta = group.translations-original(points).translations[0]
        self.assertLessEqual(np.linalg.norm(delta, axis=1).max(), .008+1e-12)
        self.assertGreater(np.linalg.norm(delta, axis=1).max(), 0)
        np.testing.assert_array_equal(np.zeros(len(group)), delta[:, 2])

    def test_safe_alternatives_survive_filter_and_dedup(self):
        data = np.load(ROOT/'OrangeSphere-collision.npz')
        group = generate(data['target'])
        detector = StableDetector(data['scene'], voxel_size=.008)
        safe = filter_then_nms(group, detector)
        c, e = detector.detect(safe, approach_dist=.06, collision_thresh=.01,
                              return_empty_grasp=True, empty_thresh=.003)
        self.assertGreater(len(safe), 1)
        self.assertFalse(np.any(c | e))


if __name__ == '__main__':
    unittest.main()


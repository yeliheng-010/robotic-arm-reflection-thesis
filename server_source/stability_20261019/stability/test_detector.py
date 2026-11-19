import unittest
import numpy as np
from grasp_process import GraspGroup
from stability.detector import StableDetector


def candidate():
    rotation = np.eye(3)
    row = np.r_[.5, .04, .02, .02, rotation.ravel(), [0, 0, .5], -1.]
    return GraspGroup(row[None])


class DetectorTests(unittest.TestCase):
    def test_distant_points_do_not_change_local_centroids(self):
        rng = np.random.RandomState(19)
        local = rng.uniform([-.02, -.035, .492], [.01, -.021, .508], (150, 3))
        first = StableDetector(local, voxel_size=.008).scene_points
        added = StableDetector(np.vstack([local, [-1.127, -.2123, .1]]), voxel_size=.008).scene_points
        added = added[np.linalg.norm(added-[0, 0, .5], axis=1) < .1]
        order = lambda p: p[np.lexsort(p.T[::-1])]
        self.assertEqual(first.shape, added.shape)
        np.testing.assert_allclose(order(first), order(added), atol=1e-12, rtol=0)

    def test_obstacle_is_rejected_and_empty_space_is_empty(self):
        rng = np.random.RandomState(3)
        obstacle = rng.uniform([-.03, -.029, .491], [.019, -.021, .509], (1000, 3))
        detector = StableDetector(obstacle, voxel_size=.008)
        collision, empty = detector.detect(candidate(), approach_dist=.06, collision_thresh=.01,
            return_empty_grasp=True, empty_thresh=.003)
        self.assertTrue(collision[0])
        self.assertTrue(empty[0])

    def test_input_order_and_values_preserved(self):
        points = np.random.RandomState(5).uniform(-.1, .1, (100, 3))
        before = points.copy()
        first = StableDetector(points, voxel_size=.008).scene_points
        second = StableDetector(points[::-1], voxel_size=.008).scene_points
        order = lambda p: p[np.lexsort(p.T[::-1])]
        np.testing.assert_array_equal(before, points)
        np.testing.assert_allclose(order(first), order(second), atol=1e-12, rtol=0)


if __name__ == '__main__':
    unittest.main()


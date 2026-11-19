"""保存的真实训练点云回归；不启动GPU或物理仿真。"""
from pathlib import Path
import unittest
import numpy as np
from grasp_process import ModelFreeCollisionDetector
from geometry.candidates import generate, original

OUT = Path('/home/yeliheng/grasp_server/geometry_20261019')


class FilterTests(unittest.TestCase):
    def surviving(self, name, generator):
        data = np.load(OUT / (name + '.npz'))
        group = generator(data['target']).nms()
        group.sort_by_score()
        detector = ModelFreeCollisionDetector(data['scene'], voxel_size=.008)
        collision, empty = detector.detect(group, approach_dist=.06, collision_thresh=.01,
                                          return_empty_grasp=True, empty_thresh=.003)
        return group[~(collision | empty)]

    def test_cylinder_collision_has_safe_candidate(self):
        name = 'GreenCylinder-collision'
        self.assertEqual(0, len(self.surviving(name, original)))
        self.assertGreater(len(self.surviving(name, generate)), 0)

    def test_sphere_none_has_safe_candidate(self):
        name = 'OrangeSphere-none'
        self.assertEqual(0, len(self.surviving(name, original)))
        self.assertGreater(len(self.surviving(name, generate)), 0)

    def test_blocked_sphere_is_still_rejected(self):
        self.assertEqual(0, len(self.surviving('OrangeSphere-collision', generate)))

    def test_original_survivors_remain_preferred(self):
        for name in ('RedBlock-none', 'GreenCylinder-none', 'PurpleCapsule-none'):
            with self.subTest(name=name):
                old = self.surviving(name, original)
                new = self.surviving(name, generate)
                np.testing.assert_array_equal(old.grasp_group_array[0], new.grasp_group_array[0])


if __name__ == '__main__':
    unittest.main()


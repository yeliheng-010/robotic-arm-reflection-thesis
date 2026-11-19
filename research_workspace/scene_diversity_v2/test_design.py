"""测试可复现性、语义与相机约定，不把生成配置当成物理成功。"""
import importlib.util
import unittest
import numpy as np


class DesignTests(unittest.TestCase):
    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec(name), '缺少待实现模块 '+name)
        return __import__(name)

    def test_factor_streams_are_shared_only_when_requested(self):
        config = self.module('sd_config')
        a = config.factors(960101, 'combined')
        for group, key in [('appearance', 'appearance'), ('camera', 'camera')]:
            self.assertEqual(a[key], config.factors(960101, group)[key])
        self.assertIsNone(config.factors(960101, 'baseline')['camera'])
        self.assertEqual(a, config.factors(960101, 'combined'))

    def test_palette_is_unique_and_labels_follow_actual_color(self):
        module = self.module('sd_appearance')
        colors = module.sample(960101)
        self.assertEqual(3, len({v['color'] for v in colors.values()}))
        labels = module.labels(colors)
        for name, value in colors.items():
            self.assertIn(value['color'], labels[name])
            self.assertEqual(1., value['rgba'][3])

    def test_camera_optical_axis_and_handedness(self):
        module = self.module('sd_camera')
        eye, target = np.array([.8, .3, 1.8]), np.array([1.2, .6, .8])
        rotation = module.look_at(eye, target)
        np.testing.assert_allclose(np.eye(3), rotation.T@rotation, atol=1e-12)
        self.assertAlmostEqual(1., np.linalg.det(rotation))
        direction = (target-eye)/np.linalg.norm(target-eye)
        np.testing.assert_allclose(direction, -rotation[:, 2], atol=1e-12)

    def test_camera_rejects_degenerate_geometry(self):
        module = self.module('sd_camera')
        with self.assertRaises(ValueError):
            module.look_at([1., 1., 1.], [1., 1., 1.])

    def test_registered_groups_and_no_heldout_tasks(self):
        module = self.module('sd_config')
        rows = module.items()
        self.assertEqual(144, len(rows))
        self.assertEqual(144, len({r['id'] for r in rows}))
        self.assertFalse(any(r['source']=='PurpleCapsule' and r['destination']=='SortingTray' for r in rows))


if __name__ == '__main__':
    unittest.main()

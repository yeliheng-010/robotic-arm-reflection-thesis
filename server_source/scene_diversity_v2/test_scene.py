"""真实编译与布局约束；不读取封存测试或执行机器人。"""
import importlib.util
import unittest
import numpy as np


class SceneTests(unittest.TestCase):
    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec(name), '缺少待实现模块 '+name)
        return __import__(name)

    def test_baseline_preserves_physics_and_camera(self):
        scene = self.module('sd_scene')
        original, _ = scene.compiled()
        from sd_config import factors
        actual, _ = scene.compiled(factors(960101, 'baseline'))
        for field in ('body_pos', 'body_quat', 'body_mass', 'geom_friction', 'cam_pos', 'cam_quat', 'cam_fovy'):
            np.testing.assert_array_equal(getattr(original, field), getattr(actual, field))

    def test_camera_and_color_reach_compiled_model(self):
        scene = self.module('sd_scene')
        from sd_config import factors
        config = factors(960101, 'combined')
        model, data = scene.compiled(config)
        cid = model.camera('cam').id
        np.testing.assert_allclose(config['camera']['position'], data.cam_xpos[cid])
        np.testing.assert_allclose(config['camera']['rotation'], data.cam_xmat[cid].reshape(3, 3))
        self.assertAlmostEqual(config['camera']['fovy'], model.cam_fovy[cid])
        for name, color in config['appearance'].items():
            gids = np.flatnonzero(model.geom_bodyid==model.body(name).id)
            self.assertGreater(len(gids), 0)
            for gid in gids:
                np.testing.assert_allclose(color['rgba'], model.geom_rgba[gid], atol=1e-7)

    def test_global_layout_is_deterministic_and_has_large_moves(self):
        layout = self.module('sd_layout')
        geometry = self.module('sd_inventory').inventory()
        for seed in (960101, 960102):
            plan = layout.sample(seed, geometry)
            self.assertTrue(plan['accepted'])
            self.assertEqual(plan, layout.sample(seed, geometry))
            self.assertGreaterEqual(min(plan['displacements'].values()), .10)
            self.assertTrue(layout.check(plan['bodies'], geometry)['passed'])


if __name__ == '__main__':
    unittest.main()

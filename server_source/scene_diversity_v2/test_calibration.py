"""回归：实际分割轮廓边界不应破坏内部深度标定检查。"""
import unittest
import cv2
import numpy as np
from sd_config import factors
from sd_scene import apply
from sd_runtime import context
from sd_render import depth_check
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv


class CalibrationTests(unittest.TestCase):
    def test_baseline_depth_reprojection(self):
        config = factors(960101, 'baseline')
        with context(config):
            env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
            renderer = None
            try:
                env.reset()
                for _ in range(500):
                    env.step()
                observation = env.render()
                renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
                roots = renderer.root_map(env.mj_data)
                self.assertTrue(depth_check(env, observation['depth'], roots)['passed'])
                env.mj_model.cam_fovy[env.mj_model.camera('cam').id] += 10.
                self.assertFalse(depth_check(env, observation['depth'], roots)['passed'])
            finally:
                if renderer is not None:
                    renderer.close()
                env.close()


if __name__ == '__main__':
    unittest.main()

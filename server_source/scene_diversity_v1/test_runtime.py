"""在真实环境验证视场同步与注入结束后的恢复。"""
import importlib.util
import unittest
import numpy as np


class RuntimeTests(unittest.TestCase):
    def test_context_restores_reset_and_dynamic_labels(self):
        self.assertIsNotNone(importlib.util.find_spec('sd_runtime'), '缺少运行适配器')
        from sd_runtime import context
        from sd_config import factors
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
        from reflection.language import LABELS, resolve_task
        before, labels = UR5GraspEnv.reset, dict(LABELS)
        config = factors(960101, 'combined')
        with context(config):
            self.assertIsNot(before, UR5GraspEnv.reset)
            instruction = '把红色方块放进'+LABELS['BlueBin']
            task = resolve_task(instruction, source='RedBlock', destination='BlueBin', parser='rule')
            self.assertEqual('BlueBin', task.destination)
        self.assertIs(before, UR5GraspEnv.reset)
        self.assertEqual(labels, LABELS)

    def test_real_render_camera_and_intrinsics_agree(self):
        self.assertIsNotNone(importlib.util.find_spec('sd_runtime'), '缺少运行适配器')
        from sd_runtime import context
        from sd_config import factors
        from sd_scene import apply
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
        from grasp_process import camera_calibration_from_env
        config = factors(960101, 'camera')
        with context(config):
            env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
            try:
                env.reset()
                observation = env.render()
                self.assertEqual((env.height, env.width), observation['depth'].shape)
                self.assertAlmostEqual(np.deg2rad(config['camera']['fovy']), env.fovy)
                _, intrinsics = camera_calibration_from_env(env)
                self.assertAlmostEqual(env.height/(2*np.tan(env.fovy/2)), intrinsics[0])
            finally:
                env.close()


if __name__ == '__main__':
    unittest.main()

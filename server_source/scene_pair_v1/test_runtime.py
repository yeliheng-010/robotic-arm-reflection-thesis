"""验证噪声通过现有传感器入口注入，退出时恢复所有补丁。"""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import numpy as np


class RuntimeTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('pair_runtime'), '缺少噪声执行适配器')
        return __import__('pair_runtime')

    def test_engine_configuration_changes_sensor_only(self):
        module = self.module()
        from pair_config import configuration
        from controlled.config import scenario
        config = configuration(960102, 'varied_noisy')
        actual = module.engine_config(config)
        expected = scenario(960102, 'clean')
        self.assertEqual(expected['bodies'], actual['bodies'])
        self.assertEqual(expected['feedback'], actual['feedback'])
        self.assertEqual(.003, actual['profile']['depth_sigma_m'])
        self.assertEqual(.02, actual['profile']['dropout'])
        self.assertEqual('varied_noisy', actual['level'])

    def test_sensor_attempt_stream_and_restore_on_exception(self):
        module = self.module()
        from pair_config import configuration
        from diversity import runtime
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
        from unittest.mock import patch
        config = module.engine_config(configuration(960102, 'varied_noisy'))
        depth = np.ones((300, 400), dtype=np.float32)
        def clean_render(_):
            return dict(img=np.zeros((300, 400, 3)), depth=depth.copy())
        with tempfile.TemporaryDirectory() as folder, patch.object(UR5GraspEnv, 'render', clean_render):
            for attempt in (1, 2):
                trace = []
                with module.sensor_attempt(attempt), \
                     runtime.sensor_context(config, 1, directory=Path(folder)/str(attempt), trace=trace):
                    noisy = UR5GraspEnv.render(None)['depth']
                self.assertEqual(attempt, trace[0]['attempt'])
                self.assertLess(abs(trace[0]['noise_rmse_m']-.003), .0001)
                self.assertLess(abs(trace[0]['dropout_fraction']-.02), .002)
                self.assertTrue(np.all(depth == 1.))
                if attempt == 1:
                    first = noisy
                else:
                    self.assertFalse(np.array_equal(first, noisy))
            self.assertIs(clean_render, UR5GraspEnv.render)
        original = runtime.sensor_context
        with self.assertRaisesRegex(RuntimeError, 'sentinel'):
            with module.sensor_attempt(2):
                raise RuntimeError('sentinel')
        self.assertIs(original, runtime.sensor_context)


if __name__ == '__main__':
    unittest.main()

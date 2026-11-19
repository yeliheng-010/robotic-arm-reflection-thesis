"""验证注入点确实返回扰动深度，且异常退出后恢复原渲染器。"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from diversity.config import scenario
from diversity.runtime import sensor_context, UR5GraspEnv


class RuntimeTests(unittest.TestCase):
    def test_paired_attempts_and_context_cleanup(self):
        original = UR5GraspEnv.render
        clean = np.ones((40, 40), dtype=np.float32)
        observation = {'depth': clean, 'img': np.zeros((40, 40, 3), dtype=np.uint8)}
        config = scenario(61000, 'medium')
        outputs = []
        with tempfile.TemporaryDirectory() as temp:
            for attempt in (1, 1, 2):
                trace = []
                with patch.object(UR5GraspEnv, 'render', lambda env: observation):
                    with sensor_context(config, attempt, directory=Path(temp), trace=trace):
                        outputs.append(UR5GraspEnv.render(None)['depth'])
                self.assertEqual(attempt, trace[0]['attempt'])
                self.assertNotEqual(trace[0]['clean_sha256'], trace[0]['noisy_sha256'])
            self.assertTrue((Path(temp)/'depth_evidence.npz').exists())
            with self.assertRaises(RuntimeError):
                with sensor_context(config, 1, directory=Path(temp), trace=[]):
                    raise RuntimeError('simulated execution failure')
        self.assertIs(original, UR5GraspEnv.render)
        np.testing.assert_array_equal(outputs[0], outputs[1])
        self.assertFalse(np.array_equal(outputs[0], outputs[2]))
        self.assertTrue(np.all(clean == 1))


if __name__ == '__main__':
    unittest.main()

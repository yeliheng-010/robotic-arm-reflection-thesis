import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1 import observe


class PauseTests(unittest.TestCase):
    def test_all_integration_entries_forbidden(self):
        env = SimpleNamespace(step=lambda: None)
        with tempfile.TemporaryDirectory() as directory, patch.object(observe, 'state', return_value=np.zeros(4)):
            with observe.paused(env, Path(directory)):
                for function in (env.step, observe.mujoco.mj_step, observe.mujoco.mj_step1, observe.mujoco.mj_step2):
                    with self.assertRaisesRegex(RuntimeError, 'Integration forbidden'):
                        function()

    def test_state_mutation_is_detected(self):
        env = SimpleNamespace(step=lambda: None)
        with tempfile.TemporaryDirectory() as directory, patch.object(observe, 'state', side_effect=[np.zeros(4), np.ones(4)]):
            with self.assertRaises(AssertionError):
                with observe.paused(env, Path(directory)):
                    pass


if __name__ == '__main__':
    unittest.main()

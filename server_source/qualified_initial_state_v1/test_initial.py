"""用真实NumPy数组覆盖prepare报告写入；环境调用全部替身。"""
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from qualified_initial_state_v1 import initial


class InitialTests(unittest.TestCase):
    def fixture(self, *, outside=False):
        qpos = np.zeros(21)
        if outside:
            qpos[13] = 2.0
        data = SimpleNamespace(qpos=qpos, qvel=np.ones(20), qacc_warmstart=np.ones(20),
            qfrc_applied=np.ones(20), xfrc_applied=np.ones((2, 6)), ctrl=np.zeros(7))
        joint = lambda name: SimpleNamespace(id=6 if name == '2f85' else int(name))
        env = SimpleNamespace(mj_model=SimpleNamespace(jnt_qposadr=np.arange(7), joint=joint),
                              mj_data=data, robot=object(), joint_names=[str(i) for i in range(6)])
        joints = [dict(range=[-1.0, 1.0], qpos_address=i) for i in range(13, 21)]
        return env, joints

    def run_prepare(self, folder, *, rejected=False, outside=False):
        env, joints = self.fixture(outside=outside)
        patches = dict(validate_model=lambda *a: None, clone_robot=lambda r: r,
            place_robot=lambda *a, **k: None, state=lambda *a: np.zeros(4),
            joint_rows=lambda *a: joints, equality_check=lambda *a: [dict(passed=not rejected)])
        with ExitStack() as stack:
            for name, value in patches.items():
                stack.enter_context(patch.object(initial, name, value))
            stack.enter_context(patch.object(initial.mujoco, 'mj_forward', lambda *a: None))
            result = initial.prepare(env, dict(command=[0.0] * 6), expected={}, folder=folder)
        return result, json.loads((folder / 'initial.json').read_text())

    def test_rejected_initial_still_saves_valid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            result, report = self.run_prepare(Path(temp), rejected=True)
        self.assertEqual(['initial_constraints'], result)
        self.assertEqual([True] * 8, report['finger_limits'])
        self.assertTrue(all(type(v) is bool for v in report['finger_limits']))

    def test_valid_initial_still_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            result, report = self.run_prepare(Path(temp))
        self.assertEqual([], result)
        self.assertEqual([True] * 8, report['finger_limits'])

    def test_out_of_range_remains_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            result, report = self.run_prepare(Path(temp), outside=True)
        self.assertEqual(['initial_constraints'], result)
        self.assertEqual([False] + [True] * 7, report['finger_limits'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

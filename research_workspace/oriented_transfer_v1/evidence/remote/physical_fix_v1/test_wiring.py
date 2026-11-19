"""真实外层包装器回归；执行器替身确保测试不产生机械臂任务运动。"""
import importlib
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import op_carry
import loopstudy.runtime as loop
from routecheck.timing import routed
from routecheck.static import state, unchanged
from cc_common import read

ROOT = Path(__file__).resolve().parents[1]
IMPL = os.environ.get('CARRY_IMPL', 'old')


def setup_case(stack, folder):
    selected = read(ROOT/'path_v2/results/audit/capsule_964345/plan.json')['selected']
    model = mujoco.MjModel.from_xml_string('<mujoco><worldbody/></mujoco>')
    env = SimpleNamespace(mj_model=model, mj_data=mujoco.MjData(model))
    robot = SimpleNamespace(get_joint=lambda: np.zeros(6),
        robot_config=SimpleNamespace(overhead=1, inline=1, wrist=-1))
    session = SimpleNamespace(folder=folder, case={'item': {}})
    check = stack.enter_context(patch.object(op_carry, 'inspect', return_value={'feasible': True}))
    stack.enter_context(patch.object(op_carry, 'clone_robot', return_value=robot))
    stack.enter_context(patch.object(op_carry, 'robot_context', return_value={}))
    runner = stack.enter_context(patch.object(grasp, '_run_planners', side_effect=lambda *a: a[4]))
    factory = op_carry.factory
    if IMPL == 'fixed':
        module = importlib.import_module('oc_runtime')
        stack.enter_context(module.wiring())
        factory = module.factory
    move = factory(grasp.move_to_point, {'selected': {'held_selection': selected}}, session=session)
    pose = op_carry.sm.SE3(np.array(selected['prefix']['pose']))
    values = dict(T_start=pose, target=tuple(selected['goal']['release'][i][3] for i in range(3)),
        action=np.zeros(7), dt=.002, time4=1.5, time5=1.5, time6=1.5,
        lift_height=selected['lift'], descend_dist=.20, keep_orientation=True)
    return SimpleNamespace(robot=robot, env=env, move=routed(move), values=values,
        check=check, runner=runner, path=folder/'live_held_check.json')


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.case = setup_case(self.stack, folder)

    def collect(self):
        c = self.case
        return loop.plans(c.move, (c.robot, c.env), c.values)

    def test_collection_has_no_guard_write_or_execution(self):
        c = self.case
        before = state(c.robot, c.env)
        for _ in range(2):
            result = self.collect()
            self.assertEqual(2, len(result['planners']))
        unchanged(before, state(c.robot, c.env))
        self.assertFalse(c.path.exists())
        c.check.assert_not_called()
        c.runner.assert_not_called()

    def test_outer_observe_executes_once_after_collection(self):
        c = self.case
        trace = {}
        wrapped = loop.observe(c.move, {'profile': 'original'}, trace)
        wrapped(c.robot, c.env, **c.values)
        self.assertTrue(trace['observation_state_unchanged'])
        self.assertTrue(c.path.exists())
        c.check.assert_called_once()
        c.runner.assert_called_once()

    def test_duplicate_execution_cannot_overwrite_or_run_twice(self):
        c = self.case
        c.move(c.robot, c.env, **c.values)
        original = c.path.read_bytes()
        with self.assertRaises(FileExistsError):
            c.move(c.robot, c.env, **c.values)
        self.assertEqual(original, c.path.read_bytes())
        c.runner.assert_called_once()

    def test_live_guard_rejection_prevents_execution(self):
        c = self.case
        c.check.return_value = {'feasible': False}
        with self.assertRaises(Exception) as caught:
            c.move(c.robot, c.env, **c.values)
        self.assertNotIsInstance(caught.exception, FileExistsError)
        self.assertFalse(read(c.path)['result']['feasible'])
        c.runner.assert_not_called()

    def test_probe_exception_restores_execution_context(self):
        c = self.case
        failed = Mock(side_effect=ValueError('probe interrupted'))
        with self.assertRaisesRegex(ValueError, 'probe interrupted'):
            loop.plans(failed, (c.robot, c.env), c.values)
        c.move(c.robot, c.env, **c.values)
        self.assertTrue(c.path.exists())
        c.runner.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)

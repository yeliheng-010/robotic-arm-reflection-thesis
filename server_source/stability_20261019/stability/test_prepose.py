"""真实MuJoCo场景中的腕部终点碰撞回归。"""
import json
import os
import unittest
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from grasp_process import GraspFlow, GraspGroup
from manipulator_grasp.arm.robot import UR5e
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from reflection.fault_injection import Fault
from stability.experiment import OUT
from stability.kinematics import set_robot_config
from stability.kinematics_probe import inspect


class PreposeTests(unittest.TestCase):
    def test_selects_collision_free_endpoint_without_moving_physics(self):
        record = json.loads((OUT/'train_v3/07/stable/result.json').read_text())['records'][0]
        group = GraspGroup(np.asarray(record['candidate_trace']['returned']))
        env = UR5GraspEnv(headless=True, model_editor=Fault('collision', 'OrangeSphere', 2000, .012).model_editor)
        try:
            with patch.object(UR5e, 'set_robot_config', set_robot_config):
                env.reset()
                for _ in range(500):
                    env.step()
                flow = GraspFlow(env, group[:1])
                initial = env.mj_data.qpos.copy()
                if not os.environ.get('CHECK_ORIGINAL_PREPOSE'):
                    from stability.prepose import select_prepose
                    select_prepose(flow, ignore=('OrangeSphere', 'BlueBin'))
                env.robot.set_joint(flow.q1)
                config = [getattr(env.robot.robot_config, n) for n in ('overhead', 'inline', 'wrist')]
                result = inspect(env, flow.T_wo, config)
                self.assertEqual([], result['arm_contacts'])
                np.testing.assert_array_equal(initial, env.mj_data.qpos)
        finally:
            env.close()


if __name__ == '__main__':
    unittest.main()


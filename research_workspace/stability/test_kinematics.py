"""世界基座和工具偏移不得改变同一关节构型的逆解分支。"""
import os
import unittest
from unittest.mock import patch
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from manipulator_grasp.arm.robot import UR5e


class KinematicsTests(unittest.TestCase):
    def test_joint_pose_roundtrip_with_world_base_and_tool(self):
        robot = UR5e()
        robot.set_base([.8, .6, .74])
        robot.set_tool(sm.SE3.Trans(0, 0, .13)*sm.SE3.RPY(-np.pi/2, -np.pi/2, 0))
        q = np.array([3.126206681054611, -.09348717069502488, -1.3155925227753258,
                      .3018836298593346, -4.705508381473407, 1.3714465142326904])
        if os.environ.get('CHECK_ORIGINAL_KINEMATICS'):
            robot.set_joint(q)
        else:
            from stability.kinematics import set_robot_config
            with patch.object(UR5e, 'set_robot_config', set_robot_config):
                robot.set_joint(q)
        actual = robot.ikine(robot.fkine(q))
        np.testing.assert_allclose(q, actual, atol=1e-8, rtol=0)


if __name__ == '__main__':
    unittest.main()

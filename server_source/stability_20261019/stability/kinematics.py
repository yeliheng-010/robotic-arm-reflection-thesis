"""在基座到法兰坐标中判断IK分支，避免世界/工具变换污染。"""
import numpy as np
from manipulator_grasp.arm.robot.robot import wrap


def set_robot_config(robot, q):
    flange = robot._base.inv() * robot.fkine(q) * robot._tool.inv()
    wrist_center = robot.cal_wpc(flange)
    theta = [q[i] + robot.theta_array[i] for i in range(robot.dof)]
    delta = wrap(np.arctan2(wrist_center[1], wrist_center[0]) - wrap(theta[0])[0])[0]
    robot.robot_config.overhead = 1 if delta <= np.pi/2 else -1
    robot.robot_config.inline = 1 if wrap(theta[2])[0] >= 0 else -1
    robot.robot_config.wrist = 1 if wrap(theta[4])[0] >= 0 else -1


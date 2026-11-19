"""末端候选不变：用完整仿真场景排除机械臂终点碰撞的IK分支。"""
from contextlib import contextmanager
import itertools
from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from reflection.sim_sensing import robot_environment_contacts

PREPOSE_RISE = .35
CONFIG_NAMES = ('overhead', 'inline', 'wrist')


def inverse(robot, pose, *, reference, config):
    robot.set_joint(reference)
    for name, value in zip(CONFIG_NAMES, config):
        setattr(robot.robot_config, name, value)
    return robot.ikine(pose)


def arm_clear(env, q, *, ignore):
    if len(q) != 6:
        return False
    data = mujoco.MjData(env.mj_model)
    data.qpos[:] = env.mj_data.qpos
    for name, angle in zip(env.joint_names, q):
        data.joint(name).qpos[0] = angle
    mujoco.mj_forward(env.mj_model, data)
    contacts = robot_environment_contacts(env.mj_model, data, ignore=ignore)
    # 静态判据仅覆盖机械臂；夹爪点云过滤与全程动态接触监控仍保留。
    return not any(pair[0] == 'ur5e_base' for pair in contacts)


def viable(flow, poses, *, config, ignore):
    joints = [inverse(flow.robot, pose, reference=flow.q1, config=config) for pose in poses]
    return joints if all(arm_clear(flow.env, q, ignore=ignore) for q in joints) else None


def choose_prepose(flow, *, ignore):
    robot = flow.robot
    robot.set_joint(flow.q1)
    default = tuple(getattr(robot.robot_config, name) for name in CONFIG_NAMES)
    approach = flow.T_wo * sm.SE3(-.1, 0, 0)
    endpoints = [approach, flow.T_wo]
    if viable(flow, endpoints, config=default, ignore=ignore):
        return {'changed': False, 'config': default}
    elevated = sm.SE3.Trans(0, 0, PREPOSE_RISE) * approach
    choices = []
    for config in itertools.product((1, -1), repeat=3):
        joints = viable(flow, [elevated]+endpoints, config=config, ignore=ignore)
        if joints is not None:
            choices.append((float(np.linalg.norm(joints[0]-flow.q1)), config, joints[0]))
    if not choices:
        return {'changed': False, 'reason': 'no_endpoint_clear_branch'}
    _, config, q = min(choices, key=lambda row: row[0])
    flow.q1 = q
    return {'changed': True, 'config': config, 'q1': q.tolist(),
            'prepose_rise': PREPOSE_RISE, 'validation': 'static_arm_endpoints_only_dynamic_guard_required'}


def select_prepose(flow, *, ignore):
    saved = flow.robot.get_joint().copy()
    try:
        return choose_prepose(flow, ignore=ignore)
    finally:
        flow.robot.set_joint(saved)


@contextmanager
def approach_context(trace, *, ignore):
    original = grasp.GraspFlow.move_to_grasp_pose

    def move(flow, *args, **kwargs):
        trace.update(select_prepose(flow, ignore=ignore))
        return original(flow, *args, **kwargs)

    with patch.object(grasp.GraspFlow, 'move_to_grasp_pose', move):
        yield

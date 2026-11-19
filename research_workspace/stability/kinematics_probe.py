"""只读静态IK诊断：区分终点不可行与路径穿障，不代替动态验证。"""
import itertools
import json
import numpy as np
import mujoco
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from grasp_process import GraspFlow, GraspGroup
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from reflection.fault_injection import Fault
from reflection.sim_sensing import robot_environment_contacts
from stability.experiment import OUT


def inspect(env, pose, config):
    robot = env.robot
    robot.set_joint([0, 0, np.pi/2, 0, -np.pi/2, 0])
    for name, value in zip(('overhead', 'inline', 'wrist'), config):
        setattr(robot.robot_config, name, value)
    q = robot.ikine(pose)
    if len(q) != 6:
        return {'reachable': False}
    data = mujoco.MjData(env.mj_model)
    data.qpos[:] = env.mj_data.qpos
    for name, angle in zip(env.joint_names, q):
        data.joint(name).qpos[0] = angle
    mujoco.mj_forward(env.mj_model, data)
    hits = robot_environment_contacts(env.mj_model, data, ignore=('OrangeSphere', 'BlueBin'))
    hits = [p for p in hits if p[0] == 'ur5e_base']
    return {'reachable': True, 'arm_contacts': hits, 'q': q.tolist(),
            'wrist_xyz': data.body('wrist_1_link').xpos.tolist()}


def main():
    record = json.loads((OUT/'train_v3/07/stable/result.json').read_text())['records'][0]
    group = GraspGroup(np.asarray(record['candidate_trace']['returned']))
    env = UR5GraspEnv(headless=True, model_editor=Fault('collision', 'OrangeSphere', 2000, .012).model_editor)
    rows = []
    try:
        env.reset()
        for _ in range(500):
            env.step()
        for index in range(len(group)):
            flow = GraspFlow(env, group[index:index+1])
            for phase, pose in [('approach_end', flow.T_wo*sm.SE3(-.1, 0, 0)), ('grasp_end', flow.T_wo)]:
                for config in itertools.product((1, -1), repeat=3):
                    rows.append(dict(index=index, phase=phase, config=config, **inspect(env, pose, config)))
    finally:
        env.close()
    (OUT/'kinematics-probe.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows))


if __name__ == '__main__':
    main()

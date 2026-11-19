"""CPU 静态预检：从冻结初态与候选重建，不渲染、不推进物理。"""
import os
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import mujoco
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from graspnetAPI import GraspGroup
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from sd_common import read, save
from sd_scene import compiled
from guard_scope import context as guard_context
from route_search import choose
from route_inputs import ROOT, inputs

JOINTS = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
          'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')


def rebuild(case):
    record = read(case['first']['result_path'])['records'][0]
    model, data = compiled(case['config'])
    data.qpos[:] = record['candidate_trace']['initial_qpos']
    mujoco.mj_forward(model, data)
    robot = UR5e()
    robot.set_base(data.body('ur5e_base').xpos.copy())
    robot.set_tool(sm.SE3.Trans(0, 0, .13)*sm.SE3.RPY(-np.pi/2, -np.pi/2, 0))
    robot.set_joint(np.array([data.joint(n).qpos[0] for n in JOINTS]))
    env = SimpleNamespace(mj_model=model, mj_data=data, robot=robot,
                          joint_names=JOINTS, height=640, width=640)
    rows = np.array(record['candidate_trace']['returned'])
    index = min(record['parameters']['candidate_index'], len(rows)-1)
    flow = grasp.GraspFlow(env, GraspGroup(rows[index:index+1]))
    flow.T_wo = sm.SE3.Trans(*record['parameters']['grasp_offset'])*flow.T_wo
    return flow, record['parameters']


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    for case in inputs():
        if case['reused_success']:
            continue
        with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
            flow, parameters = rebuild(case)
            result = choose(flow, item=case['item'], parameters=parameters, excluded=set(),
                            hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
        save(ROOT/('preflight_'+case['id']+'.json'), result)
        print(case['id'], 'checked', len(result['candidates']),
              'selected', (result['selected'] or {}).get('id'), flush=True)


if __name__ == '__main__':
    main()

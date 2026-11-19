"""从冻结初态重新构造几何检查，避免信任运行时自报可行。"""
from types import SimpleNamespace
from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
import grasp_process as grasp
import stability.prepose as prepose
from stability.kinematics import set_robot_config
from manipulator_grasp.arm.robot import UR5e
from cl_geometry import compiled
from cl_design import configuration
from cm_planning import choose
from cm_pose import eligible


def restore(context, item, layout):
    model,data = compiled(configuration(item,layout))
    data.qpos[:] = context['qpos']
    mujoco.mj_forward(model,data)
    env = SimpleNamespace(mj_model=model,mj_data=data,joint_names=context['joint_names'],height=480,width=640)
    robot = UR5e()
    robot._base = sm.SE3(np.array(context['base']))
    robot.robot.base = robot._base
    robot.set_tool(sm.SE3(np.array(context['tool'])))
    robot.q0 = np.array(context['robot_q'])
    for name,value in zip(('overhead','inline','wrist'),context['config']):
        setattr(robot.robot_config,name,value)
    return SimpleNamespace(env=env,robot=robot,q0=np.array(context['q0']),q1=np.array(context['q1']),
        T_wo=sm.SE3(np.array(context['nominal'])))


def check_nominal(flow, record, parameters):
    candidates = record['candidate_trace']['returned']
    row = np.array(candidates[min(parameters['candidate_index'],len(candidates)-1)])
    camera,_ = grasp.camera_calibration_from_env(flow.env)
    nominal = camera*sm.SE3.Rt(sm.SO3(row[4:13].reshape(3,3)),row[13:16])
    nominal = sm.SE3.Trans(*parameters['grasp_offset'])*nominal
    np.testing.assert_allclose(nominal.A,flow.T_wo.A,atol=1e-8,rtol=0)
    np.testing.assert_allclose(record['candidate_trace']['initial_qpos'],flow.env.mj_data.qpos,atol=1e-8,rtol=0)


def check_extension(record, item, layout, *, policy, feedback):
    trace = record['motion_extension']
    active = policy=='geometry' and eligible(feedback)
    assert trace['policy']==policy and trace['active']==active and trace['feedback']==feedback
    assert trace['training_approved'] is False
    if not active:
        assert set(trace)=={'policy','active','feedback','training_approved'}
        return dict(active=False,selected=None,fallback=None)
    context = trace['context']
    assert context['parameters']==record['parameters']
    flow = restore(context,item,layout)
    check_nominal(flow,record,record['parameters'])
    hooks = (grasp.move_to_grasp_pose,grasp.move_to_point,prepose.select_prepose)
    with patch.object(UR5e,'set_robot_config',set_robot_config):
        expected = choose(flow,hooks,parameters=record['parameters'],item=item)
    for key,value in expected.items():
        assert trace[key]==value, 'Static replay mismatch: '+key
    selected = trace['selected']
    fallback = 'original_rule_pose_no_static_feasible_candidate' if selected is None else None
    assert trace['fallback']==fallback
    if record['execution_adapter'] and selected is not None:
        pose = trace['candidates'][selected]['pose']
        np.testing.assert_allclose(pose,record['execution_adapter']['start'],atol=1e-6,rtol=0)
    return dict(active=True,selected=selected,fallback=fallback)

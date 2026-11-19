"""沿用现有预抓取分支选择，额外抽样检查抓取和运输路径。"""
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from routecheck.clone import clone_robot
from routecheck.static import CONFIG, state, unchanged
from cm_pose import poses, select
from cm_geometry import inspect
from loopstudy.actions import canonical

RELEASE_OFFSET = .12
PHASES = ('pregrasp','approach','grasp','lift','transport','descent')


def context(flow, parameters):
    return dict(qpos=flow.env.mj_data.qpos.tolist(),q0=flow.q0.tolist(),q1=flow.q1.tolist(),
        nominal=flow.T_wo.A.tolist(),base=flow.robot._base.A.tolist(),tool=flow.robot._tool.A.tolist(),
        robot_q=flow.robot.get_joint().tolist(),joint_names=list(flow.env.joint_names),
        config=[getattr(flow.robot.robot_config,n) for n in CONFIG],parameters=parameters)


def collect(flow, original, *, parameters, target):
    segments = []
    def intercept(*args, **kwargs):
        for planner,duration in zip(args[2],args[3][1:]):
            segments.append((PHASES[len(segments)],planner,duration))
        return args[4]
    duration = parameters['time_scale']
    with patch.object(grasp,'_run_planners',intercept):
        original[0](flow.robot,flow.env,q0=flow.q0,q1=flow.q1,T_wo=flow.T_wo,
            time1=duration,time2=duration,time3=duration,action=np.zeros(7))
        original[1](flow.robot,flow.env,T_start=flow.T_wo,target=target,action=np.zeros(7),
            time4=duration,time5=duration,time6=duration,lift_height=parameters['lift_height'])
    assert len(segments)==6
    return segments


def evaluate(flow, option, hooks, *, parameters, item):
    clone = clone_robot(flow.robot)
    proxy = SimpleNamespace(robot=clone,env=flow.env,q0=flow.q0.copy(),q1=flow.q1.copy(),T_wo=option['pose'])
    ignore = (item['source'],item['destination'])
    prepose = hooks[2](proxy,ignore=ignore)
    target = flow.env.mj_data.body(item['destination']).xpos.copy()
    target += np.array(parameters['place_offset'])+np.array([0.,0.,RELEASE_OFFSET])
    segments = collect(proxy,hooks[:2],parameters=parameters,target=tuple(target))
    checker = clone_robot(flow.robot)
    result = inspect(checker,flow.env,segments,ignore=ignore)
    return dict(id=option['id'],pose=option['pose'].A.tolist(),q1=proxy.q1.tolist(),
        prepose=canonical(prepose),target=target.tolist(),**result)


def choose(flow, hooks, *, parameters, item):
    before = state(flow.robot,flow.env)
    saved = context(flow,parameters)
    rows = [evaluate(flow,option,hooks,parameters=parameters,item=item) for option in poses(flow.T_wo)]
    unchanged(before,state(flow.robot,flow.env))
    index = select(rows)
    return dict(context=saved,candidates=rows,selected=index,unchanged=True,
        scope='simulation_geometry_expert_open_gripper_static_path',
        limitations=['discrete_samples','held_object_not_predicted','dynamic_tracking_not_predicted',
                     'source_destination_and_support_contacts_excluded'])

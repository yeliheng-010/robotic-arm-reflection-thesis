"""固定候选搜索，不使用未来物理成败或按案例设参数。"""
from itertools import product
from types import SimpleNamespace
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from routecheck.clone import clone_robot
from routecheck.static import state, unchanged
from stability.prepose import inverse
from cm_planning import collect, context, RELEASE_OFFSET
from cm_pose import poses
from route_geometry import inspect
from route_policy import first_feasible

LIFTS = (.35, .45, .55)
CONFIGS = tuple(product((1, -1), repeat=3))


def options(nominal):
    for pose in poses(nominal):
        for lift in LIFTS:
            for config in CONFIGS:
                name = pose['id']+'_'+str(lift)+'_'+','.join(map(str, config))
                yield dict(id=name, pose=pose['pose'], lift=lift, config=config)


def evaluate(flow, option, *, item, parameters, hooks):
    robot = clone_robot(flow.robot)
    elevated = sm.SE3.Trans(0, 0, option['lift'])*option['pose']*sm.SE3(-.1, 0, 0)
    q1 = inverse(robot, elevated, reference=flow.q1, config=option['config'])
    base = dict(id=option['id'], pose=option['pose'].A.tolist(), lift=option['lift'],
                config=list(option['config']), q1=np.asarray(q1).tolist())
    if len(q1) != 6:
        return dict(base, feasible=False, failure=dict(reason='prepose_ik'))
    proxy = SimpleNamespace(robot=robot, env=flow.env, q0=flow.q0.copy(), q1=np.array(q1), T_wo=option['pose'])
    params = dict(parameters, lift_height=option['lift'])
    target = flow.env.mj_data.body(item['destination']).xpos.copy()
    target += np.array(parameters['place_offset'])+np.array([0., 0., RELEASE_OFFSET])
    segments = collect(proxy, hooks, parameters=params, target=tuple(target))
    result = inspect(clone_robot(flow.robot), flow.env, segments, item=item)
    return dict(base, target=target.tolist(), **result)


def choose(flow, *, item, parameters, excluded, hooks):
    before = state(flow.robot, flow.env)
    saved = context(flow, parameters)
    rows = []
    for option in options(flow.T_wo):
        if option['id'] in excluded:
            rows.append(dict(id=option['id'], feasible=False, failure=dict(reason='previously_executed')))
            continue
        rows.append(evaluate(flow, option, item=item, parameters=parameters, hooks=hooks))
        if rows[-1]['feasible']:
            break
    unchanged(before, state(flow.robot, flow.env))
    return dict(context=saved, candidates=rows, selected=first_feasible(rows, excluded),
                excluded=sorted(excluded), unchanged=True,
                limitations=['discrete_static_samples', 'open_gripper', 'held_object_not_predicted', 'tracking_not_predicted'])

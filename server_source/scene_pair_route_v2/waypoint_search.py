"""预抓取高度和搬运高度独立搜索；先检查前缀再搜索运输。"""
from itertools import product
from types import SimpleNamespace
import numpy as np
import spatialmath as sm
from cm_pose import poses
from cm_planning import context, RELEASE_OFFSET
from routecheck.clone import clone_robot
from routecheck.static import state, unchanged
from stability.prepose import inverse
from route_geometry import inspect
from waypoint_policy import RISES, LIFTS, ROUTES
from waypoint_paths import corridor, collect

CONFIGS = tuple(product((1, -1), repeat=3))
CONFIG_NAMES = ('overhead', 'inline', 'wrist')


def options(flow):
    for pose in poses(flow.T_wo):
        yield dict(id=pose['id']+'_safe', pose=pose['pose'], rise=None, config=None)
        for rise in RISES:
            for config in CONFIGS:
                name = pose['id']+'_'+str(rise)+'_'+','.join(map(str, config))
                yield dict(id=name, pose=pose['pose'], rise=rise, config=config)


def prepose(flow, option):
    robot = clone_robot(flow.robot)
    if option['rise'] is None:
        q1 = flow.q1.copy()
    else:
        elevated = sm.SE3.Trans(0, 0, option['rise'])*option['pose']*sm.SE3(-.1, 0, 0)
        q1 = inverse(robot, elevated, reference=flow.q1, config=option['config'])
    if len(q1) == 6:
        robot.set_joint(q1)
    return dict(id=option['id'], pose=option['pose'].A.tolist(), rise=option['rise'],
                q1=np.asarray(q1).tolist(), config=[getattr(robot.robot_config,n) for n in CONFIG_NAMES])


def proxy(flow, row):
    return SimpleNamespace(robot=clone_robot(flow.robot), env=flow.env,
                           q0=flow.q0.copy(), q1=np.array(row['q1']), T_wo=sm.SE3(np.array(row['pose'])))


def carry(flow, row, checker, *, item, parameters, hooks, edges):
    target = flow.env.mj_data.body(item['destination']).xpos.copy()
    target += np.array(parameters['place_offset'])+np.array([0., 0., RELEASE_OFFSET])
    results = []
    for lift in LIFTS:
        for route in ROUTES:
            params = dict(parameters, lift_height=lift)
            segments = collect(proxy(flow, row), hooks[1], parameters=params, phase='carry',
                               route=route, edges=edges, target=target)
            check = inspect(clone_robot(checker), flow.env, segments, item=item)
            result = dict(row, id=row['id']+'_'+str(lift)+'_'+route, lift=lift,
                          transport_route=route, target=target.tolist(), **check)
            results.append(result)
            if check['feasible']:
                break
        if results[-1]['feasible']:
            break
    return results


def explore(flow, *, item, parameters, hooks, edges):
    prefixes, candidates = [], []
    for option in options(flow):
        row = prepose(flow, option)
        if len(row['q1']) != 6:
            prefixes.append(dict(row, feasible=False, failure=dict(reason='prepose_ik')))
            continue
        for route in ROUTES:
            segments = collect(proxy(flow, row), hooks[0], parameters=parameters,
                               phase='prefix', route=route, edges=edges)
            checker = clone_robot(flow.robot)
            check = inspect(checker, flow.env, segments, item=item)
            current = dict(row, id=row['id']+'_'+route, approach_route=route, **check)
            prefixes.append(current)
            if not check['feasible'] and check['phase'] == 'pregrasp':
                break
            if not check['feasible']:
                continue
            candidates.extend(carry(flow, current, checker, item=item, parameters=parameters,
                                    hooks=hooks, edges=edges))
            if candidates[-1]['feasible']:
                return prefixes, candidates
    return prefixes, candidates


def choose(flow, *, item, parameters, hooks):
    before = state(flow.robot, flow.env)
    saved = context(flow, parameters)
    edges = corridor(flow.env, item['destination'])
    prefixes, candidates = explore(flow, item=item, parameters=parameters, hooks=hooks, edges=edges)
    unchanged(before, state(flow.robot, flow.env))
    selected = next((r for r in candidates if r['feasible']), None)
    return dict(context=saved, prefixes=prefixes, candidates=candidates, selected=selected,
                edges=[v.tolist() for v in edges], unchanged=True,
                limitations=['open_gripper','held_object_not_predicted','tracking_not_predicted','discrete_samples'])

"""只替换候选来源；沿用原完整路径和关节保护。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
import goal_search
import goal_geometry
import goal_endpoints
import waypoint_search
import waypoint_paths
from model_grasp_gpu_v1.planning import search, deadline
from routecheck.clone import clone_robot
from route_geometry import inspect as robot_check
from hv_geometry import inspect as held_check
from jg_paths import context as path_context
from rh_planner import select as home
from qualified_path_v1.observed import targets


def forbidden_truth(*args, **kwargs):
    raise RuntimeError('Oracle target/corridor generation is forbidden')


@contextmanager
def observed_scope(geometry, proposal):
    pose = sm.SE3(np.asarray(proposal['pose']))
    def poses(nominal):
        np.testing.assert_array_equal(nominal.A, pose.A)
        return [dict(id='model_observed', pose=pose)]
    def inspect(robot, env, segments, *, item):
        if segments[0][0] == 'lift':
            return held_check(robot, env, segments, item=item, grasp=pose)
        return robot_check(robot, env, segments, item=item)
    with ExitStack() as stack:
        stack.enter_context(patch.object(goal_geometry, 'geometry', forbidden_truth))
        stack.enter_context(patch.object(waypoint_paths, 'corridor', forbidden_truth))
        stack.enter_context(patch.object(goal_endpoints, 'geometry', lambda *_: geometry))
        stack.enter_context(patch.object(goal_endpoints, 'targets', targets))
        stack.enter_context(patch.object(goal_search, 'corridor', lambda *_: np.asarray(geometry['edges'])))
        stack.enter_context(patch.object(goal_search, 'inspect', inspect))
        for module in (goal_endpoints, waypoint_search):
            stack.enter_context(patch.object(module, 'poses', poses))
        yield


def strict(flow, plan, *, case):
    row, parameters = plan['selected'], case['state']['parameters']
    checker = clone_robot(flow.robot)
    with path_context():
        proxy = goal_search.proxy(flow, row)
        prefix = waypoint_paths.collect(proxy, grasp.move_to_grasp_pose, parameters=parameters,
            phase='prefix', route=row['approach_route'], edges=np.asarray(plan['edges']))
        first = robot_check(checker, flow.env, prefix, item=case['item'])
        if not first['feasible']:
            return dict(passed=False, prefix=first)
        carry = waypoint_paths.collect(proxy, grasp.move_to_point, parameters=dict(parameters, lift_height=row['lift']),
            phase='carry', route=row['transport_route'], edges=np.asarray(plan['edges']), target=row['target'])
        held = held_check(checker, flow.env, carry, item=case['item'], grasp=sm.SE3(np.asarray(row['pose'])))
    if not held['feasible']:
        return dict(passed=False, prefix=first, held=held)
    returned = home(checker, flow.env, flow.q0, duration=parameters['time_scale'], item=case['item'])
    return dict(passed=returned['selected'] is not None, prefix=first, held=held, return_home=returned,
        dynamic_tracking_verified=False, post_release_recheck_required=True, physical_attempts=0)


def run(flow, case, *, geometry, proposal):
    events = []
    with observed_scope(geometry, proposal), \
         patch.object(goal_search, 'LIFTS', (case['state']['parameters']['lift_height'],)), deadline(240):
        plan = search(flow, case, events)
        checked = strict(flow, plan, case=case) if plan['selected'] is not None else dict(passed=False)
    return dict(plan=plan, strict=checked, joint_events=events)

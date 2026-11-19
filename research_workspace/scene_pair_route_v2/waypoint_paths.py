"""静态检查和执行共用相同的分段规划器。"""
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from route_geometry import groups, bounds
from waypoint_policy import CORRIDOR_MARGIN_M

PREFIX = ('pregrasp', 'approach', 'grasp')
CARRY = ('lift', 'transport', 'descent')


def corridor(env, destination):
    ids = groups(env.mj_model, destination)[1]
    low, high = bounds(env.mj_model, env.mj_data)
    return (np.min(low[ids], axis=0)[:2]-CORRIDOR_MARGIN_M,
            np.max(high[ids], axis=0)[:2]+CORRIDOR_MARGIN_M)


def waypoint(start, end, route, *, edges):
    low, high = edges
    xyz = (start.t+end.t)/2
    xyz[2] = max(start.t[2], end.t[2])
    if route.startswith('x_'):
        xyz[0] = low[0] if route.endswith('low') else high[0]
    elif route.startswith('y_'):
        xyz[1] = low[1] if route.endswith('low') else high[1]
    else:
        x, y = route.split('_')
        xyz[0], xyz[1] = (low[0] if x=='low' else high[0]), (low[1] if y=='low' else high[1])
    return sm.SE3.Rt(start.R, xyz)


def cartesian(start, end, duration):
    position = grasp.LinePositionParameter(start.t, end.t)
    attitude = grasp.OneAttitudeParameter(sm.SO3(start.R), sm.SO3(end.R))
    path = grasp.CartesianParameter(position, attitude)
    velocity = grasp.QuinticVelocityParameter(duration)
    return grasp.TrajectoryPlanner(grasp.TrajectoryParameter(path, velocity))


class Compound:
    def __init__(self, planners, duration):
        self.planners, self.leg_duration = planners, duration

    def interpolate(self, time):
        index = min(max(int(time/self.leg_duration), 0), len(self.planners)-1)
        return self.planners[index].interpolate(min(max(time-index*self.leg_duration, 0), self.leg_duration))


def detour(planner, duration, *, route, edges):
    if route == 'direct':
        return planner, duration
    start, end = planner.interpolate(0), planner.interpolate(duration)
    via = waypoint(start, end, route, edges=edges)
    return Compound([cartesian(start, via, duration), cartesian(via, end, duration)], duration), 2*duration


def expand(phase, planner, duration):
    if isinstance(planner, Compound):
        return [(phase+'.'+str(i), p, planner.leg_duration) for i,p in enumerate(planner.planners)]
    return [(phase, planner, duration)]


def inject(original, route, *, edges):
    def run(*args, **kwargs):
        assert not kwargs and len(args[2]) == 3
        values = list(args)
        planners, durations = list(values[2]), list(values[3])
        planners[1], durations[2] = detour(planners[1], durations[2], route=route, edges=edges)
        values[2], values[3] = planners, durations
        return original(*values)
    return run


def collect(flow, original, *, parameters, phase, route, edges, target=None):
    rows = []
    names = PREFIX if phase == 'prefix' else CARRY
    def intercept(*args, **kwargs):
        for name, planner, duration in zip(names, args[2], args[3][1:]):
            rows.extend(expand(name, planner, duration))
        return args[4]
    duration = parameters['time_scale']
    with patch.object(grasp, '_run_planners', intercept):
        if phase == 'prefix':
            # 原预抓取执行器分三次调用_run_planners；只在接近段替换。
            rows.clear()
            return collect_prefix(flow, original, duration=duration, route=route, edges=edges)
        with patch.object(grasp, '_run_planners', inject(intercept, route, edges=edges)):
            original(flow.robot, flow.env, T_start=flow.T_wo, target=tuple(target), action=np.zeros(7),
                     time4=duration, time5=duration, time6=duration, lift_height=parameters['lift_height'])
    return rows


def collect_prefix(flow, original, *, duration, route, edges):
    rows, phase = [], [0]
    def intercept(*args, **kwargs):
        assert len(args[2]) == 1
        name = PREFIX[phase[0]]
        planner, seconds = args[2][0], args[3][1]
        if name == 'approach':
            planner, seconds = detour(planner, seconds, route=route, edges=edges)
        rows.extend(expand(name, planner, seconds))
        phase[0] += 1
        return args[4]
    with patch.object(grasp, '_run_planners', intercept):
        original(flow.robot, flow.env, q0=flow.q0, q1=flow.q1, T_wo=flow.T_wo,
                 time1=duration, time2=duration, time3=duration, action=np.zeros(7))
    assert phase[0] == 3
    return rows

"""静态路径使用原关节候选算法，缓存相同关节端点的检查。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import waypoint_paths
from routecheck.clone import clone_robot
from rh_planner import select, planners


def choose(flow, segment, *, item):
    phase, planner, duration = segment
    assert phase == 'pregrasp'
    start, goal = planner.interpolate(0.), planner.interpolate(duration)
    assert isinstance(start, np.ndarray) and start.shape == goal.shape == (6,)
    robot = clone_robot(flow.robot)
    robot.set_joint(start.copy())
    return select(robot, flow.env, goal, duration=duration, item=item)


def replacement(original, *, item, ledger):
    cache = {}
    def collect(flow, hook, **kwargs):
        rows = original(flow, hook, **kwargs)
        phase, planner, duration = rows[0]
        assert phase == 'pregrasp'
        key = (tuple(planner.interpolate(0.)), tuple(planner.interpolate(duration)), float(duration))
        if key not in cache:
            cache[key] = choose(flow, rows[0], item=item)
            ledger.append(cache[key])
        option = cache[key]['selected']
        if option is None:
            # 只返回给原静态检查器，原危险直达仍会被拒绝，不能执行。
            return rows
        prefix = [('pregrasp', p, t) for p,t in zip(planners(option), option['durations'])]
        return prefix+rows[1:]
    return collect


@contextmanager
def context(item, ledger):
    wrapper = replacement(waypoint_paths.collect_prefix, item=item, ledger=ledger)
    with patch.object(waypoint_paths, 'collect_prefix', wrapper):
        yield

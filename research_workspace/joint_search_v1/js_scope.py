"""只在对应预抓取终点使用已审计路径，其他候选仍受原检查。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import waypoint_paths
from js_geometry import segments


def wrapper(original, selection):
    def collect(flow, hook, **kwargs):
        rows = original(flow,hook,**kwargs)
        phase, planner, duration = rows[0]
        assert phase == 'pregrasp'
        path = selection['path']
        start, goal = planner.interpolate(0.), planner.interpolate(duration)
        if np.array_equal(start,path[0]) and np.array_equal(goal,path[-1]):
            return segments(path,duration)+rows[1:]
        return rows
    return collect


@contextmanager
def context(selection):
    with patch.object(waypoint_paths,'collect_prefix',wrapper(waypoint_paths.collect_prefix,selection)):
        yield

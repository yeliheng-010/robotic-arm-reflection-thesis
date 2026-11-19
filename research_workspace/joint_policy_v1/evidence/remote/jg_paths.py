"""将选中路段随候选传递，静态与执行读取同一时长和关节端点。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import goal_search
import goal_audit_geometry
import waypoint_paths
from rh_planner import planners


def proxy_wrapper(original):
    def proxy(flow, row):
        result = original(flow,row)
        result.joint_option = row.get('joint_option')
        return result
    return proxy


def prefix_wrapper(original):
    def collect(flow, hook, **kwargs):
        rows = original(flow,hook,**kwargs)
        option = getattr(flow,'joint_option',None)
        if option is None:
            return rows
        phase,planner,seconds = rows[0]
        assert phase == 'pregrasp'
        np.testing.assert_array_equal(planner.interpolate(0.),option['waypoints'][0])
        np.testing.assert_allclose(planner.interpolate(seconds),option['waypoints'][-1],atol=1e-12,rtol=0)
        changed = [('pregrasp',p,t) for p,t in zip(planners(option),option['durations'])]
        return changed+rows[1:]
    return collect


@contextmanager
def context():
    with patch.object(goal_search,'proxy',proxy_wrapper(goal_search.proxy)), \
         patch.object(goal_audit_geometry,'proxy',proxy_wrapper(goal_audit_geometry.proxy)), \
         patch.object(waypoint_paths,'collect_prefix',prefix_wrapper(waypoint_paths.collect_prefix)):
        yield

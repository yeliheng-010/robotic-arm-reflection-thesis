"""从保存的规划采样与关节状态重建原51点几何检查，不执行动作。"""
from types import SimpleNamespace
from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from sd_scene import compiled
from guard_scope import context as guard_context
from route_geometry import inspect, SAMPLES, CLEARANCE_M


class RecordedPlanner:
    def __init__(self, leg):
        self.rows, self.duration = leg['samples'], leg['duration']
        assert len(self.rows) == SAMPLES

    def interpolate(self, time):
        index = int(round(time/self.duration*(SAMPLES-1)))
        value = np.array(self.rows[index])
        return sm.SE3(value) if value.shape == (4, 4) else value


def rebuild(case, context):
    model, data = compiled(case['config'])
    data.qpos[:] = context['qpos']
    mujoco.mj_forward(model, data)
    robot = UR5e()
    robot._base = sm.SE3(np.array(context['base']))
    robot.robot.base = robot._base
    robot.set_tool(sm.SE3(np.array(context['tool'])))
    robot.set_joint(np.array(context['robot_q']))
    for name, value in zip(('overhead', 'inline', 'wrist'), context['config']):
        setattr(robot.robot_config, name, value)
    env = SimpleNamespace(mj_model=model, mj_data=data, joint_names=context['joint_names'])
    return robot, env


def group(case, row):
    robot, env = rebuild(case, row['context'])
    segments = [(leg['phase'], RecordedPlanner(leg), leg['duration']) for leg in row['legs']]
    result = inspect(robot, env, segments, item=case['item'])
    expected = row['result']
    for field in ('feasible', 'samples', 'phase', 'time'):
        assert result[field] == expected[field], (field, result, expected)
    if result['failure']:
        assert result['failure']['reason'] == expected['failure']['reason']
    assert row['executed'] == result['feasible']
    if row['executed']:
        assert row['end_time'] >= row['start_time']
        assert row['end_time']-row['start_time'] <= sum(row['durations'])+.02
    return dict(feasible=result['feasible'], samples=result['samples'], executed=row['executed'])


def audit(case, trace):
    assert CLEARANCE_M == .010 and SAMPLES == 51
    assert trace['requested'] == case['state']['parameters']
    if trace.get('grasp'):
        grasp = trace['grasp']
        np.testing.assert_allclose(np.array(trace['nominal_grasp_xyz'])+[.005, 0, 0],
                                   grasp['actual_target'], atol=1e-9, rtol=0)
        assert grasp['requested_offset'] == [.005, 0, 0] and grasp['durations'] == [1.5]*3
    if trace.get('carry'):
        assert trace['carry']['durations'] == [1.5]*3
        assert trace['carry']['lift_height'] == case['state']['parameters']['lift_height']
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
        rows = [group(case, r) for r in trace['planners']]
    return dict(passed=True, groups=rows, clearance_m=CLEARANCE_M,
                actual_motion=any(r['executed'] for r in rows), grasp_checked=bool(trace.get('grasp')),
                carry_checked=bool(trace.get('carry')))

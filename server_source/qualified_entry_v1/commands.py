"""调用原生入口收集命令，保留原保护，禁止执行积分。"""
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
import goal_search
import waypoint_paths
from routecheck.clone import clone_robot
from route_geometry import inspect as robot_check
from hv_geometry import inspect as held_check
from jg_paths import context as path_context
from rh_runtime import wrapper as return_wrapper
from live_motion import plan_values

NUMERIC_ATOL = 1e-12


def expected(flow, plan, *, parameters):
    row = plan['selected']
    with path_context():
        proxy = goal_search.proxy(flow, row)
        prefix = waypoint_paths.collect(proxy, grasp.move_to_grasp_pose, parameters=parameters,
            phase='prefix', route=row['approach_route'], edges=np.asarray(plan['edges']))
        carry = waypoint_paths.collect(proxy, grasp.move_to_point, parameters=dict(parameters, lift_height=row['lift']),
            phase='carry', route=row['transport_route'], edges=np.asarray(plan['edges']), target=row['target'])
    return prefix, carry


def compare(actual, expected):
    left, right = plan_values(actual), plan_values(expected)
    assert len(left) == len(right)
    error = 0.
    for a, b in zip(left, right):
        assert a['phase'] == b['phase'] and a['duration'] == b['duration']
        np.testing.assert_allclose(a['samples'], b['samples'], atol=NUMERIC_ATOL, rtol=0)
        error = max(error, float(np.max(np.abs(np.asarray(a['samples'])-b['samples']))))
    return dict(passed=True, segments=len(left), max_component_error=error)


class Capture:
    def __init__(self, case, pose):
        self.case, self.pose = case, pose
        self.phase, self.rows, self.checks = 'prefix', [], []

    def backend(self, *values):
        robot, env, planners, durations, action, dt = values
        names = ('pregrasp', 'approach', 'grasp') if self.phase == 'prefix' else ('lift', 'transport', 'descent')
        if self.phase == 'return':
            names = tuple('return_'+str(len(self.rows)+i) for i in range(len(planners)))
        elif self.phase == 'prefix':
            names = (names[len(self.rows)],)
        segments = list(zip(names, planners, durations[1:]))
        checker = clone_robot(robot)
        if self.phase == 'carry':
            result = held_check(checker, env, segments, item=self.case['item'], grasp=self.pose)
        else:
            result = robot_check(checker, env, segments, item=self.case['item'])
        self.rows.extend(segments)
        self.checks.append(result)
        assert result['feasible'], result
        robot.set_joint(checker.get_joint().copy())
        return action.copy()


def run(flow, case, *, plan, folder):
    row, parameters = plan['selected'], case['state']['parameters']
    # 当前获准方案为直达且无额外关节路点；其他方案必须另接线验证。
    assert row['approach_route'] == row['transport_route'] == 'direct' and not row.get('joint_option')
    prefix, carry = expected(flow, plan, parameters=parameters)
    native = grasp.GraspFlow.from_env(flow.env)
    native.robot, native.q0 = clone_robot(flow.robot), flow.q0.copy()
    native.q1, native.T_wo = np.asarray(row['q1']), sm.SE3(np.asarray(row['pose']))
    capture, duration = Capture(case, native.T_wo), parameters['time_scale']
    with patch.object(grasp, '_run_planners', capture.backend):
        native.move_to_grasp_pose(time1=duration, time2=duration, time3=duration)
        prefix_match = compare(capture.rows, prefix)
        capture.phase, capture.rows = 'carry', []
        native.move_to_point(tuple(row['target']), time4=duration, time5=duration,
            time6=duration, lift_height=row['lift'], z_offset=0.)
        carry_match = compare(capture.rows, carry)
        capture.phase, capture.rows = 'return', []
        with patch.object(grasp, 'step8_go_home', return_wrapper(grasp.step8_go_home,
                item=case['item'], folder=folder)):
            native.back_to_zero(time7=duration, time8=duration)
    return dict(passed=True, prefix_match=prefix_match, carry_match=carry_match,
        checks=capture.checks, actual_return_legs=plan_values(capture.rows),
        includes_native_retract=True, post_release_state_verified=False,
        gripper_contact_verified=False, physical_attempts=0)

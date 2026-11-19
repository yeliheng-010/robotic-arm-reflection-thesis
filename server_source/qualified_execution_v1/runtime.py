"""固定模型命令，仅安全拒绝与原回程规划使用私有状态。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from reflection import monitors
from routecheck.clone import clone_robot
from route_geometry import inspect as robot_check
from hv_geometry import inspect as held_check
from rh_runtime import wrapper as return_wrapper, robot_context
from live_motion import plan_values
from qualified_entry_v1.commands import expected, compare
from qualified_execution_v1.common import SETTLE_STEPS

TICK_STRIDE = 10


def native_flow(env, plan):
    row = plan['selected']
    assert row['approach_route'] == row['transport_route'] == 'direct' and not row.get('joint_option')
    flow = grasp.GraspFlow.from_env(env)
    flow.q1, flow.T_wo = np.asarray(row['q1']), sm.SE3(np.asarray(row['pose']))
    np.testing.assert_array_equal(flow.q0, plan['context']['q0'])
    return flow


class GuardedBackend:
    def __init__(self, flow, case, *, plan, trace):
        self.flow, self.case, self.trace = flow, case, trace
        self.expected_prefix, self.expected_carry = expected(flow, plan, parameters=case['state']['parameters'])
        self.phase, self.prefix_index = 'prefix', 0
        self.original = grasp._run_planners

    def run(self, *values):
        robot, env, planners, durations = values[:4]
        if self.phase == 'prefix':
            expected_rows = self.expected_prefix[self.prefix_index:self.prefix_index+1]
            self.prefix_index += 1
        else:
            expected_rows = self.expected_carry if self.phase == 'carry' else None
        names = [r[0] for r in expected_rows] if expected_rows else [f'return_{i}' for i in range(len(planners))]
        segments = list(zip(names, planners, durations[1:]))
        matched = compare(segments, expected_rows) if expected_rows else dict(post_release_replanned=True)
        context = robot_context(robot, env)
        checker = clone_robot(robot)
        if self.phase == 'carry':
            result = held_check(checker, env, segments, item=self.case['item'], grasp=self.flow.T_wo)
        else:
            result = robot_check(checker, env, segments, item=self.case['item'])
        row = dict(phase=self.phase, context=context, legs=plan_values(segments), result=result,
            matched=matched, executed=False, start_time=float(env.mj_data.time))
        self.trace.append(row)
        if not result['feasible']:
            monitors.abort(monitors.ErrorType.COLLISION, 'Current path rejected', guard_kind='live_path')
        row['executed'] = True
        try:
            return self.original(*values)
        finally:
            row['end_time'] = float(env.mj_data.time)


@contextmanager
def live_monitor(flow, item, *, counts):
    monitor = monitors.ExecutionMonitor(flow.env, item['source'], item['destination'])
    original = flow.env.step
    def step(*args, **kwargs):
        result = original(*args, **kwargs)
        counts['steps'] += 1
        if counts['steps'] % TICK_STRIDE == 0:
            hits = monitors.robot_environment_contacts(flow.env.mj_model, flow.env.mj_data,
                ignore=(item['source'], item['destination']))
            if hits:
                monitors.abort(monitors.ErrorType.COLLISION, 'Forbidden live contact', contacts=hits)
            monitor.tick()
        return result
    with patch.object(flow.env, 'step', step):
        yield monitor


def execute(flow, case, *, plan, folder, trace, stages, counts):
    row, duration = plan['selected'], case['state']['parameters']['time_scale']
    # 私有残差只供原监视器记录错误，不生成或修正任何动作。
    residual = flow.T_wo.t[:2]-flow.env.mj_data.body(case['item']['source']).xpos[:2]
    backend = GuardedBackend(flow, case, plan=plan, trace=trace)
    with patch.object(grasp, '_run_planners', backend.run), live_monitor(flow, case['item'], counts=counts) as monitor:
        stages.append('approach_started')
        flow.move_to_grasp_pose(time1=duration, time2=duration, time3=duration)
        stages.append('close_started')
        flow.close_gripper()
        monitor.check_grasp(residual)
        stages.append('grasp_confirmed')
        backend.phase, monitor.phase = 'carry', 'carry'
        flow.move_to_point(tuple(row['target']), time4=duration, time5=duration,
            time6=duration, lift_height=row['lift'], z_offset=0.)
        stages.append('release_started')
        monitor.phase = 'release'
        flow.open_gripper()
        stages.append('released')
        for _ in range(SETTLE_STEPS):
            flow.env.step(flow.action)
        backend.phase = 'return'
        with patch.object(grasp, 'step8_go_home', return_wrapper(grasp.step8_go_home,
                item=case['item'], folder=folder)):
            flow.back_to_zero(time7=duration, time8=duration)
        stages.append('returned_home')

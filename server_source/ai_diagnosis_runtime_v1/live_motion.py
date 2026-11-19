"""只核验显式命令并检查原规划，不替策略改姿态或放置目标。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from reflection.monitors import abort, ErrorType
from routecheck.clone import clone_robot
from route_geometry import inspect, SAMPLES


def init_wrapper(original, trace):
    def initialize(flow, *args, **kwargs):
        original(flow, *args, **kwargs)
        flow._ai_nominal_grasp = flow.T_wo.t.copy()
        trace['nominal_grasp_xyz'] = flow._ai_nominal_grasp.tolist()
    return initialize


def grasp_wrapper(original, trace, *, parameters):
    def move(flow, *args, **kwargs):
        expected = flow._ai_nominal_grasp + np.array(parameters['grasp_offset'])
        np.testing.assert_allclose(expected, flow.T_wo.t, atol=1e-9, rtol=0)
        times = [kwargs[k] for k in ('time1', 'time2', 'time3')]
        assert times == [parameters['time_scale']]*3
        trace['grasp'] = dict(requested_offset=parameters['grasp_offset'], actual_target=flow.T_wo.t.tolist(),
                              expected_target=expected.tolist(), durations=times, passed=True)
        return original(flow, *args, **kwargs)
    return move


def carry_wrapper(original, trace, *, parameters):
    def move(flow, target, **kwargs):
        times = [kwargs[k] for k in ('time4', 'time5', 'time6')]
        assert times == [parameters['time_scale']]*3
        assert kwargs['lift_height'] == parameters['lift_height']
        trace['carry'] = dict(target=list(target), durations=times,
                             lift_height=kwargs['lift_height'], z_offset=kwargs['z_offset'], passed=True)
        return original(flow, target, **kwargs)
    return move


def plan_values(segments):
    rows = []
    for phase, planner, duration in segments:
        samples = []
        for time in np.linspace(0., duration, SAMPLES):
            value = planner.interpolate(float(time))
            samples.append(value.tolist() if isinstance(value, np.ndarray) else value.A.tolist())
        rows.append(dict(phase=phase, duration=duration, samples=samples))
    return rows


def checked_planners(original, trace, *, item, recorder):
    def run(*args, **kwargs):
        assert not kwargs and len(args) == 6
        robot, env, planners, durations = args[:4]
        assert durations[0] == 0. and len(planners) == len(durations)-1
        segments = [(recorder.action+f'_{i}', p, float(t)) for i, (p, t) in enumerate(zip(planners, durations[1:]))]
        saved = dict(qpos=env.mj_data.qpos.tolist(), robot_q=robot.get_joint().tolist(),
                     base=robot._base.A.tolist(), tool=robot._tool.A.tolist(), joint_names=list(env.joint_names),
                     config=[getattr(robot.robot_config, n) for n in ('overhead', 'inline', 'wrist')])
        result = inspect(clone_robot(robot), env, segments, item=item)
        row = dict(action=recorder.action, context=saved, legs=plan_values(segments), result=result,
                   durations=list(durations), executed=False)
        trace['planners'].append(row)
        if not result['feasible']:
            abort(ErrorType.COLLISION, 'Planned path rejected by fixed geometry guard',
                  guard_kind='path_admissibility', route_planning_rejected=True)
        row['executed'] = True
        row['start_time'] = float(env.mj_data.time)
        try:
            return original(*args, **kwargs)
        finally:
            row['end_time'] = float(env.mj_data.time)
    return run


@contextmanager
def context(item, state, *, recorder, trace):
    parameters = state['parameters']
    trace.update(requested=parameters, planners=[])
    with ExitStack() as stack:
        stack.enter_context(patch.object(grasp.GraspFlow, '__init__', init_wrapper(grasp.GraspFlow.__init__, trace)))
        stack.enter_context(patch.object(grasp.GraspFlow, 'move_to_grasp_pose',
                            grasp_wrapper(grasp.GraspFlow.move_to_grasp_pose, trace, parameters=parameters)))
        stack.enter_context(patch.object(grasp.GraspFlow, 'move_to_point',
                            carry_wrapper(grasp.GraspFlow.move_to_point, trace, parameters=parameters)))
        stack.enter_context(patch.object(grasp, '_run_planners',
                            checked_planners(grasp._run_planners, trace, item=item, recorder=recorder)))
        yield

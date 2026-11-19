"""提供任务结果与命令执行事实，不提供错误类别、根因或修复建议。"""
import math

ACTIONS = {'move_to_grasp_pose', 'close_gripper', 'move_to_point', 'open_gripper', 'back_to_zero'}


def number(value):
    assert type(value) in (int, float) and math.isfinite(value)
    return float(value)


def planner(row, index):
    assert row['action'] in ACTIONS
    assert type(row['executed']) is bool and type(row['result']['feasible']) is bool
    assert row['executed'] == row['result']['feasible']
    duration = sum(number(value) for value in row['durations'])
    assert duration > 0
    value = dict(sequence=index, action=row['action'], geometry_admitted=row['result']['feasible'],
                 motion_started=row['executed'], planned_duration_s=duration, elapsed_s=None)
    if row['executed']:
        elapsed = number(row['end_time'])-number(row['start_time'])
        assert 0 <= elapsed <= duration+.02
        value['elapsed_s'] = elapsed
    return value


def public(step, bridge):
    assert type(step['success']) is bool and type(step['index']) is int and 1 <= step['index'] <= 3
    assert bridge['requested'] == step['state']['parameters']
    return dict(attempt=step['index'], task_completed=step['success'],
        task_result_source='existing_simulation_task_evaluator_boolean_only',
        command_execution=[planner(row, i+1) for i, row in enumerate(bridge['planners'])],
        interpretation='Motion started does not establish completion; geometry admission is not physical success.')

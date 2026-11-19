"""只读检查完整意图/返回/观察序列，不把部分证据当完整轨迹。"""
from qualified_closure_mjb_v1.protocol import BUDGET, read, require, commands
from qualified_closure_dynamics_v1.worker import reasons


def trace_contract(folder, *, allow_verification=False):
    result = read(folder/'result.json')
    count = result['completed_steps']
    require(type(count) is int and 0 <= count <= BUDGET['task_steps'], 'Invalid completed count')
    require(result['uncertain_step'] is None and result['error'] is None, 'Incomplete trajectory')
    require(result['task_step_requests'] == result['task_step_returns'] == count, 'Native counts differ')
    require(result['observed_steps'] == count and result['setup_steps'] == 0, 'Observation/setup count')
    expected = {f'{kind}_{i:04d}.{suffix}' for kind, suffix, start in
                (('state', 'npz', 0), ('observed', 'json', 0), ('intent', 'json', 1))
                for i in range(start, count+1)}
    actual = {p.name for pattern in ('state_*.npz', 'observed_*.json', 'intent_*.json')
              for p in folder.glob(pattern)}
    require(actual == expected, 'Missing or extra trace file')
    controls = commands()
    for index in range(count+1):
        row = read(folder/f'observed_{index:04d}.json')
        require(row['step'] == row['task_steps'] == index, 'Sequence mismatch')
        if index < count:
            require(not reasons(row), 'Integrated after stop condition')
        if index:
            require(read(folder/f'intent_{index:04d}.json') ==
                    dict(step=index, gripper_command=controls[index-1]), 'Wrong command')
    stop = reasons(row) or (['budget_exhausted'] if count == BUDGET['task_steps'] else ['wall_timeout'])
    if allow_verification:
        require(count == 0 and result.get('mode') == 'verification', 'Invalid verification evidence')
        stop = reasons(row) or ['verification_only']
    require(result['reasons'] == stop, 'Wrong stop reason')
    return count

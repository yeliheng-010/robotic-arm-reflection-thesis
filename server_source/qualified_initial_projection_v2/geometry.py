"""从旧after状态绑定原XML残差；不读取尝试角作为初值。"""
import numpy as np
from qualified_projection_diagnostic_v1.common import STATE, PARAMETERS, read
from qualified_projection_diagnostic_v1.geometry import PARTS, SIDES, evaluate
from qualified_initial_projection_v2.problem import ScaledProblem


def problem_for_side(side):
    if side not in SIDES:
        raise ValueError('Unknown side')
    parameters = read(PARAMETERS)
    with np.load(STATE, allow_pickle=False) as data:
        source = data['after']
    values = {'2f85': source[7:14].copy()}
    joints = {row['name']: row for row in parameters['joints']}
    for name, row in joints.items():
        values[name] = source[1+row['qpos_address']]
    names = [f'{side}_{part}_joint' for part in PARTS]
    reference = np.array([values[name] for name in names])
    limits = np.array([joints[name]['range'] for name in names])
    def residual(angles):
        changed = dict(values)
        changed.update(zip(names, angles))
        return np.asarray(evaluate(changed, parameters)[SIDES.index(side)]['base'])
    return ScaledProblem(reference, limits, residual=residual)

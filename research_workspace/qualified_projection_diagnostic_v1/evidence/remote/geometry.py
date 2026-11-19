"""仅由原XML代数评价保存角度及其微分。"""
import numpy as np
from qualified_initial_state_v1.algebra import residuals, poses
from qualified_projection_diagnostic_v1.common import XML, PARAMETERS, STATE, read

SIDES = ('right', 'left')
PARTS = ('coupler', 'spring_link', 'follower')
CONNECT_TOL = 1e-7
DRIVER_TOL = 1e-7
CHANGE_CAP = 0.01


def saved_values(result):
    parameters = read(PARAMETERS)
    with np.load(STATE, allow_pickle=False) as data:
        source = data['after']
    values = {'2f85': source[7:14].copy()}
    changes = []
    for row in parameters['joints']:
        name = row['name']
        old = float(source[1 + row['qpos_address']])
        side, part = name.split('_', 1)
        part = part.removesuffix('_joint')
        new = old if part == 'driver' else result['solutions'][side]['angles'][PARTS.index(part)]
        values[name] = new
        changes.append(dict(name=name, original=old, saved=new, delta=new-old,
                            within_range=bool(row['range'][0] <= new <= row['range'][1])))
    return values, parameters, changes


def evaluate(values, parameters):
    rows = residuals(XML, values, parameters['equalities'])
    base = poses(XML, values)['base'][1]
    for row in rows:
        row['base'] = (base.T @ np.asarray(row['world'])).tolist()
    return rows


def geometry_check(result):
    values, parameters, changes = saved_values(result)
    rows = evaluate(values, parameters)
    for side, row in zip(SIDES, rows):
        np.testing.assert_allclose(result['solutions'][side]['base_frame_residual'],
                                   row['base'], atol=1e-12, rtol=0)
        row['max_world_abs'] = float(np.max(np.abs(row['world'])))
        row['passed'] = row['max_world_abs'] <= CONNECT_TOL
    eq = next(row for row in parameters['equalities'] if row['type'] == 2)
    x, y = (values[name] for name in eq['names'])
    driver = x - sum(c * y**p for p, c in enumerate(eq['data'][:5]))
    limits = all(row['within_range'] and abs(row['delta']) <= CHANGE_CAP for row in changes)
    fixed = all(row['delta'] == 0 for row in changes if 'driver' in row['name'])
    passed = all(row['passed'] for row in rows) and limits and fixed and abs(driver) <= DRIVER_TOL
    return dict(saved_value_geometry_passed=bool(passed), connections=rows, changes=changes,
                original_ranges_and_change_cap_passed=bool(limits), driver_fixed=fixed,
                driver_residual=driver, original_rejection_preserved=True,
                executable_state_created=False), values, parameters


def constraint_at(values, parameters, *, side):
    def constraint(angles):
        point = dict(values)
        for part, angle in zip(PARTS, angles):
            point[f'{side}_{part}_joint'] = angle
        row = evaluate(point, parameters)[SIDES.index(side)]
        return np.asarray(row['base'])[1:] / 1e-3
    return constraint

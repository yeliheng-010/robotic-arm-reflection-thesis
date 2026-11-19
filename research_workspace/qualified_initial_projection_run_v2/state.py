"""合成副本的最小状态修改与独立状态掩码检查。"""
import numpy as np
from qualified_closure_dynamics_v1.protocol import require
from qualified_initial_state_v1.algebra import residuals
from qualified_projection_diagnostic_v1.common import STATE, XML, PARAMETERS, read

SIDES = ('right', 'left')
PARTS = ('coupler', 'spring_link', 'follower')
MAX_CHANGE, CONNECT_TOL, DRIVER_TOL = 0.01, 1e-7, 1e-7


def source_state():
    with np.load(STATE, allow_pickle=False) as data:
        return data['after'].copy()


def check(source, candidate, parameters):
    require(source.shape == candidate.shape and np.isfinite(candidate).all(), 'Invalid state')
    allowed = [1+row['qpos_address'] for row in parameters['joints'] if 'driver' not in row['name']]
    require(len(allowed) == 6 and len(set(allowed)) == 6, 'Wrong passive joint mask')
    mask = np.ones(source.size, dtype=bool)
    mask[allowed] = False
    np.testing.assert_array_equal(source[mask], candidate[mask])
    require(np.max(np.abs(candidate[allowed]-source[allowed])) <= MAX_CHANGE, 'Change cap exceeded')
    values = {'2f85': candidate[7:14]}
    for row in parameters['joints']:
        value = float(candidate[1+row['qpos_address']])
        require(row['range'][0] <= value <= row['range'][1], 'Original limit exceeded')
        values[row['name']] = value
    eq = next(row for row in parameters['equalities'] if row['type'] == 2)
    x, y = (values[name] for name in eq['names'])
    driver = x-sum(c*y**p for p, c in enumerate(eq['data'][:5]))
    require(abs(driver) <= DRIVER_TOL, 'Driver equality failed')
    return values, dict(other_state_unchanged=True, driver_residual=driver,
                       allowed_indices=allowed, changed_indices=np.flatnonzero(source != candidate).tolist())


def assemble(solutions):
    require(set(solutions) == set(SIDES), 'Incomplete side results')
    if not all(row['accepted'] and row['optimizer_success'] for row in solutions.values()):
        return None, dict(candidate_created=False, rejection='side_solver_rejected')
    source = source_state()
    parameters = read(PARAMETERS)
    candidate = source.copy()
    joints = {row['name']: row for row in parameters['joints']}
    for side in SIDES:
        for part, angle in zip(PARTS, solutions[side]['angles']):
            candidate[1+joints[f'{side}_{part}_joint']['qpos_address']] = angle
    values, contract = check(source, candidate, parameters)
    rows = residuals(XML, values, parameters['equalities'])
    require(all(np.max(np.abs(row['world'])) <= CONNECT_TOL for row in rows), 'Full connection failed')
    return dict(integration=candidate, reference=source), dict(candidate_created=True,
        state_contract=contract, connections=rows, geometry_feasible=True)

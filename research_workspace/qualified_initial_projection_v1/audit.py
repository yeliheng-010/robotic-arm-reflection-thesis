"""独立公式检查新候选的限位、等式和状态修改范围；不构造模型。"""
import os
import numpy as np
from qualified_closure_dynamics_v3.guarded_imports import zero_motion
from qualified_initial_state_v1.algebra import residuals
from qualified_initial_projection_v1.common import (
    RUN, XML, PARAMETERS, read, save, sha, require, verify, input_states)


def state_checks(source, candidate, parameters):
    require(source.shape == candidate.shape and np.isfinite(candidate).all(), 'Invalid candidate state')
    allowed = [1 + row['qpos_address'] for row in parameters['joints'] if 'driver' not in row['name']]
    mask = np.ones(source.size, dtype=bool)
    mask[allowed] = False
    np.testing.assert_array_equal(source[mask], candidate[mask])
    require(np.max(np.abs(source[allowed] - candidate[allowed])) <= 0.01, 'Change cap exceeded')
    values = {'2f85': candidate[7:14]}
    for row in parameters['joints']:
        value = float(candidate[1 + row['qpos_address']])
        require(row['range'][0] <= value <= row['range'][1], 'Original joint range exceeded')
        values[row['name']] = value
    eq = next(row for row in parameters['equalities'] if row['type'] == 2)
    first, second = (values[name] for name in eq['names'])
    driver = first - sum(c * second**p for p, c in enumerate(eq['data'][:5]))
    require(abs(driver) <= 1e-7, 'Driver equality mismatch')
    return values, driver


def check_candidate(parameters, result):
    with np.load(RUN / 'candidate_state.npz', allow_pickle=False) as data:
        candidate, source = data['integration'], data['reference']
    np.testing.assert_array_equal(input_states()['after'], source)
    values, driver = state_checks(source, candidate, parameters)
    rows = residuals(XML, values, parameters['equalities'])
    for expected, row in zip(result['connections'], rows):
        for frame in ('world', 'local'):
            np.testing.assert_allclose(expected[frame], row[frame], atol=1e-12, rtol=0)
        require(np.max(np.abs(row['world'])) <= 1e-7, 'Independent connection rejection')
    for side in ('right', 'left'):
        solved = result['solutions'][side]
        require(solved['attempts'] == 1 and solved['accepted'], 'Unexpected solver history')
    return dict(candidate_verified=True, connections=rows, driver_residual=driver,
        other_state_unchanged=True, original_ranges_passed=True, change_cap_passed=True,
        candidate_sha256=sha(RUN / 'candidate_state.npz'))


def main():
    checked = verify()
    for name, digest in read(RUN / 'inventory.json').items():
        require(sha(RUN / name) == digest, 'Candidate evidence changed: ' + name)
    save(RUN / 'audit_claim.json', dict(consumed=1, integration_budget=0, job=os.environ['SLURM_JOB_ID']))
    result = read(RUN / 'result.json')
    with zero_motion() as counts:
        if result['candidate_created']:
            checked_candidate = check_candidate(read(PARAMETERS), result)
        else:
            require(not (RUN / 'candidate_state.npz').exists(), 'Rejected candidate was saved')
            require(any(not row['accepted'] for row in result['solutions'].values()), 'Invalid rejection')
            checked_candidate = dict(candidate_verified=False, rejection_evidence_only=True)
        require(not any(counts.values()), 'Unexpected construction/integration')
    save(RUN / 'audit_result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'], counts=counts,
        imports=checked, **checked_candidate, result_sha256=sha(RUN / 'result.json'),
        method='independent_original_xml_algebra_and_state_mask',
        full_scene_checked=False, production_ready=False, dynamics_validated=False))
    print(dict(passed=True, counts=counts, **checked_candidate), flush=True)


if __name__ == '__main__':
    main()

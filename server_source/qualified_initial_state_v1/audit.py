"""独立进程以XML刚体公式复算；禁止全部MuJoCo构造和积分。"""
import os
import numpy as np
from qualified_closure_dynamics_v3.guarded_imports import zero_motion
from qualified_initial_state_v1.algebra import residuals
from qualified_initial_state_v1.common import (
    RUN, XML, PARAMETERS, read, save, sha, require, verify, input_states, recorded_equalities)


def compare(states, parameters, result):
    all_rows = {}
    for label, state in states.items():
        values = {'2f85': state[7:14]}
        for row in parameters['joints']:
            values[row['name']] = float(state[1 + row['qpos_address']])
        rows = residuals(XML, values, parameters['equalities'])
        for expected, row in zip(result['states'][label], rows):
            for frame in ('world', 'local'):
                np.testing.assert_allclose(expected[frame], row[frame], atol=1e-12, rtol=0)
        all_rows[label] = rows
    recorded = recorded_equalities()
    for row in all_rows['after']:
        np.testing.assert_allclose(recorded[row['id']]['residual'], row['world'], atol=1e-12, rtol=0)
    for before, after in zip(all_rows['before'], all_rows['after']):
        np.testing.assert_allclose(before['local'], after['local'], atol=1e-12, rtol=0)
    return all_rows


def main():
    checked = verify()
    for name, digest in read(RUN / 'inventory.json').items():
        require(sha(RUN / name) == digest, 'Diagnostic artifact changed: ' + name)
    save(RUN / 'audit_claim.json', dict(consumed=1, job=os.environ['SLURM_JOB_ID'], integration_budget=0))
    result = read(RUN / 'result.json')
    with zero_motion() as counts:
        rows = compare(input_states(), read(PARAMETERS), result)
        require(not any(counts.values()), 'Unexpected construction/integration')
    save(RUN / 'audit_result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'], counts=counts,
        imports=checked, formula_rows=rows, method='original_xml_rigid_body_algebra',
        recorded_after_reproduced=True, result_sha256=sha(RUN / 'result.json'),
        source_xml_sha256=sha(XML), safety_gate_changed=False, dynamics_validated=False))
    print(dict(passed=True, counts=counts, independent_formula_matches=True), flush=True)


if __name__ == '__main__':
    main()

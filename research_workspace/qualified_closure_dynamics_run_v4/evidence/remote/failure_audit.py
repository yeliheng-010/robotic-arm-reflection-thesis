"""只读审计初态保存失败；不导入MuJoCo、不创建场景或积分。"""
import ast
import json
import os
import sys
from pathlib import Path
import numpy as np
from qualified_closure_dynamics_v4.protocol import (
    ROOT as ENGINE, RUN, PROJECT, read, save, sha, require, verify_authorization)

ROOT = Path(__file__).resolve().parent
ERROR = 'TypeError: Object of type bool_ is not JSON serializable'


def partial_initial():
    path = RUN / 'initial.json'
    text = path.read_text(encoding='utf-8')
    try:
        json.loads(text)
    except json.JSONDecodeError as error:
        parse_error = str(error)
    else:
        raise ValueError('Expected truncated initial record')
    require(text.rstrip().endswith('"finger_limits": ['), 'Unexpected truncation location')
    offset = text.index('"equalities":') + len('"equalities":')
    rows, _ = json.JSONDecoder().raw_decode(text[offset:].lstrip())
    checked = []
    for row in rows:
        residual = np.asarray(row['residual'])
        passed = bool(residual.size and np.isfinite(residual).all()
                      and np.max(np.abs(residual)) <= row['tolerance'])
        require(passed == row['passed'], 'Recorded equality evaluation differs')
        checked.append(dict(id=row['id'], name=row['name'], type=row['type'],
            maximum_residual=float(np.max(np.abs(residual))), tolerance=row['tolerance'], passed=passed))
    require(any(not row['passed'] for row in checked), 'Expected initial constraint rejection evidence')
    return dict(original_json_valid=False, json_error=parse_error,
        stopped_at='finger_limits_first_value', complete_prefix_equalities=checked,
        equality_values_independently_recomputed=False,
        numeric_threshold_evaluation_recomputed=True, model_unavailable=True,
        would_reject_even_after_serialization_fix=True)


def reproduction():
    value = -1.0 <= np.float64(0.0) <= 1.0
    require(type(value) is np.bool_, 'Unexpected NumPy comparison type')
    try:
        json.dumps(dict(finger_limits=[value]), allow_nan=False)
    except TypeError as error:
        message = type(error).__name__ + ': ' + str(error)
    else:
        raise ValueError('Expected NumPy boolean serialization failure')
    require(message == ERROR, 'Different serialization error')
    source = PROJECT / 'qualified_closure_dynamics_v1/initial.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare')
    bounds = next(n for n in ast.walk(function) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'bounds' for t in n.targets))
    require(isinstance(bounds.value, ast.ListComp) and isinstance(bounds.value.elt, ast.Compare),
            'Bounds expression changed')
    returned = next(n for n in ast.walk(function) if isinstance(n, ast.Return))
    require('all((row[\'passed\'] for row in checks))' in ast.unparse(returned)
            or "all(row['passed'] for row in checks)" in ast.unparse(returned), 'Rejection contract changed')
    with np.load(RUN / 'initial_transform.npz', allow_pickle=False) as values:
        require(set(values.files) == {'before', 'after'}, 'Unexpected transform archive')
        before, after = values['before'], values['after']
        require(before.shape == after.shape and np.isfinite(before).all() and np.isfinite(after).all(),
                'Invalid saved integration vectors')
        state = dict(shape=list(before.shape), changed_elements=int(np.count_nonzero(before != after)))
    return dict(reproduced_error=message, comparison_type='numpy.bool_', source_sha256=sha(source),
        source_expression=ast.unparse(bounds.value), rejection_return=ast.unparse(returned),
        fixture_is_synthetic_scalar=True, saved_transform=state, simulation_imported=False)


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    save(ROOT / 'audit_attempt.json', dict(consumed=1, scope='initial_save_failure_evidence_only',
        job=os.environ['SLURM_JOB_ID'], source_sha256=sha(Path(__file__)),
        launcher_sha256=sha(ROOT / 'failure_audit.sbatch')))
    auth = verify_authorization(ENGINE / 'authorization.json')
    registration = read(ROOT / 'registration.json')
    require(sha(ENGINE / 'authorization.json') == registration['authorization_sha256'], 'Authorization changed')
    for name, digest in registration['sources'].items():
        require(sha(name) == digest, 'Wrapper changed: ' + name)
    require({p.name for p in RUN.iterdir()} == {'claim.json', 'imports.json', 'initial_transform.npz',
            'initial.json', 'failure.json'}, 'Unexpected run artifacts')
    claim, failure = read(RUN / 'claim.json'), read(RUN / 'failure.json')
    require(claim['consumed'] == 1 and claim['job'] == '6859', 'Claim mismatch')
    require(claim['authorization_sha256'] == registration['authorization_sha256'], 'Claim binding changed')
    require(failure == dict(error=ERROR, setup_step_requests=500, task_step_requests=0), 'Unexpected failure')
    require('6859|FAILED|1:0|' in (ROOT / 'execution_status.txt').read_text(), 'Job status mismatch')
    prefix, serialization = partial_initial(), reproduction()
    require(not any(name == 'mujoco' or name.startswith('mujoco.') for name in sys.modules), 'Simulation imported')
    paths = [*RUN.iterdir(), ENGINE / 'authorization.json', ROOT / 'registration.json',
             ROOT / 'execute-6859.log', ROOT / 'execution_status.txt',
             PROJECT / 'qualified_closure_dynamics_v1/initial.py']
    result = dict(passed=True, scope='initial_save_failure_evidence_only', job=os.environ['SLURM_JOB_ID'],
        verified_identities=len(auth['identities']), execution_failed=True, claim_consumed=1,
        setup_step_requests=500, task_step_requests=0, audit_integration_steps=0,
        simulation_imported=False, dynamics_validated=False, production_ready=False, retry_allowed=False,
        partial_initial=prefix, serialization=serialization,
        identities={str(p): sha(p) for p in paths})
    save(ROOT / 'failure_audit.json', result)
    print({key: result[key] for key in ('passed', 'scope', 'verified_identities', 'claim_consumed',
          'setup_step_requests', 'task_step_requests', 'dynamics_validated')}, flush=True)


if __name__ == '__main__':
    main()

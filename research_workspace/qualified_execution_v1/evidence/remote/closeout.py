"""核验冻结来源与失败结论；保留原数值完全相等审计失败。"""
import ast
import subprocess
from qualified_execution_v1.common import ROOT, RUN, read, save, sha, verify


def verify_inputs():
    manifest = verify()
    execution = read(RUN/'execution_manifest.json')
    for name, digest in execution['identities'].items():
        assert sha(name) == digest, name
    assert read(RUN/'attempt_claim.json') == dict(consumed=1,
        execution_manifest_sha256=sha(RUN/'execution_manifest.json'))
    for prefix in ('contact_audit', 'state_diagnostic'):
        frozen = read(RUN/f'{prefix}_manifest.json')
        assert sha(ROOT/f'{prefix}.py') == frozen['source_sha256']
        for name, digest in frozen['identities'].items():
            assert sha(name) == digest, name
    return dict(source_identities=len(manifest['identities']),
        execution_identities=len(execution['identities']), consumed_physical_attempts=1)


def verify_failure():
    recorded = read(RUN/'physical/result.json')
    contact = read(RUN/'contact_audit.json')
    state = read(RUN/'state_diagnostic.json')
    assert recorded['physical_attempts'] == 1 and recorded['steps'] == 3040
    assert recorded['stages'] == ['approach_started', 'close_started']
    assert not any(recorded[k] for k in ('completed', 'success', 'physical_placement'))
    assert recorded['safety_error']['error_type'] == 'collision'
    assert contact['live_rejection_reproduced'] and contact['actual_contacts'] == state['actual_contacts']
    assert len(contact['actual_contacts']) == 2
    assert not contact['final_scene_initial_fingers']
    assert contact['final_scene_commanded_arm'] == contact['initial_scene_commanded_arm_final_fingers']
    assert state['physical_verdict_identical'] and state['task_verdict_identical']
    assert not state['rebuilt_success'] and not state['final_evaluation_identical']
    assert set(state['differences']) == {'position', 'placement_residual_xy', 'xy_error_m', 'tilt_deg'}
    assert len(state['paths']) == 3 and all(p['feasible'] and p['executed'] for p in state['paths'])
    assert not read(RUN/'physical/publication.json')['model_input_published']
    for prefix in ('initial_observation', 'final_observation'):
        assert read(RUN/f'physical/{prefix}/isolation.json')['passed']
    assert read(RUN/'physical/initial_observation/qualification.json')['accepted']
    assert not read(RUN/'physical/final_observation/qualification.json')['accepted']
    return dict(failure_verdict_corroborated=True, contact_reproduced=True,
        original_exact_audit_passed=False, original_exact_audit_failure_preserved=True,
        numeric_differences=state['differences'], dynamic_cause_proven=False)


def source_checks():
    files = list(ROOT.glob('*.py'))
    for path in files:
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300, path
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path, node.name)
    return len(files)


def main():
    result = dict(frozen=verify_inputs(), findings=verify_failure(), source_files_checked=source_checks(),
        physical_attempts_added=0, model_calls=0, training_runs=0)
    jobs = subprocess.run(['sacct', '-j', '6729,6730,6731,6732,6755,6756',
        '--format=JobID,State,ExitCode,Elapsed', '-n', '-P'], check=True, capture_output=True, text=True)
    result['job_accounting'] = jobs.stdout
    identities = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*')
        if p.is_file() and not p.name.startswith('closeout-') and '__pycache__' not in p.parts}
    save(RUN/'closeout_inventory.json', dict(files=identities))
    result['inventory_sha256'] = sha(RUN/'closeout_inventory.json')
    save(RUN/'closeout_result.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()

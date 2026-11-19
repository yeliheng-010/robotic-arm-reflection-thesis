"""本地核对原始失败档案，不导入仿真或执行实验。"""
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT, REMOTE = ROOT.parent, ROOT / 'evidence/remote'
SERVER = '/home/yeliheng/grasp_server/'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def files():
    delivery = read(ROOT / 'evidence/DELIVERY.json')
    lookup, matches = {}, 0
    for row in delivery['files']:
        archive = REMOTE / row['name']
        assert sha(archive) == row['sha256'], row['name']
        lookup[SERVER + row['remote']] = archive
        local = PROJECT / row['remote']
        if local.is_file():
            assert sha(local) == row['sha256'], row['remote']
            matches += 1
    checks = delivery['checks']
    assert checks['v3_run_status'] == 404
    prior_auth = PROJECT / 'qualified_closure_dynamics_run_v3/evidence/remote/engine/authorization.json'
    assert sha(prior_auth) == checks['v3_authorization_sha256']
    old_claim = PROJECT / 'qualified_closure_dynamics_run_v1/evidence/remote/engine/run/claim.json'
    assert sha(old_claim) == sha(REMOTE / 'history/v1_claim.json')
    return lookup, dict(downloaded=len(delivery['files']), local_source_matches=matches,
                        old_claim_and_v3_authorization_preserved=True)


def lineage(lookup):
    auth = read(REMOTE / 'engine/authorization.json')
    prepared = PROJECT / 'qualified_closure_dynamics_v4/evidence/remote/prepared/manifest.json'
    registration = read(REMOTE / 'registration.json')
    assert auth['preparation_sha256'] == sha(prepared)
    assert auth['identities'] == read(prepared)['identities']
    assert auth['execution_authorized'] and auth['budget'] == registration['budget']
    assert sha(REMOTE / 'engine/authorization.json') == registration['authorization_sha256']
    for name, digest in registration['sources'].items():
        assert sha(lookup[name]) == digest, name
    for name, digest in registration['gpu_check_hashes'].items():
        assert sha(prepared.parent / name) == digest
    claim = read(REMOTE / 'engine/run/claim.json')
    assert claim['consumed'] == 1 and claim['job'] == '6859'
    assert claim['authorization_sha256'] == registration['authorization_sha256']
    assert claim['diagnostic_id'] == auth['diagnostic_id'] == 'qualified_closure_dynamics_v4-978505'
    frozen = [p for p in (PROJECT / 'qualified_closure_dynamics_v4').glob('*.py')
              if SERVER + p.relative_to(PROJECT).as_posix() in auth['identities']]
    for source in frozen:
        assert sha(source) == auth['identities'][SERVER + source.relative_to(PROJECT).as_posix()]
    return dict(authorized_identities=len(auth['identities']), frozen_v4_python_sources=len(frozen),
                consumed_diagnostic_claim=1, registration_job=registration['job'])


def failure(lookup):
    folder = REMOTE / 'engine/run'
    assert {p.name for p in folder.iterdir()} == {'claim.json', 'imports.json', 'initial_transform.npz',
                                                 'initial.json', 'failure.json'}
    actual, audit = read(folder / 'failure.json'), read(REMOTE / 'failure_audit.json')
    assert actual == dict(error='TypeError: Object of type bool_ is not JSON serializable',
                          setup_step_requests=500, task_step_requests=0)
    assert audit['passed'] and audit['scope'] == 'initial_save_failure_evidence_only'
    assert audit['setup_step_requests'] == 500 and audit['task_step_requests'] == 0
    assert audit['audit_integration_steps'] == 0 and not audit['simulation_imported']
    assert not audit['dynamics_validated'] and not audit['production_ready']
    for name, digest in audit['identities'].items():
        assert sha(lookup[name]) == digest, name
    attempt = read(REMOTE / 'audit_attempt.json')
    assert attempt['consumed'] == 1 and attempt['job'] == '6860'
    assert sha(ROOT / 'failure_audit.py') == attempt['source_sha256']
    assert sha(ROOT / 'failure_audit.sbatch') == attempt['launcher_sha256']
    partial = (folder / 'initial.json').read_text()
    try:
        json.loads(partial)
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError('Original truncated JSON unexpectedly repaired')
    offset = partial.index('"equalities":') + len('"equalities":')
    rows, _ = json.JSONDecoder().raw_decode(partial[offset:].lstrip())
    rejected = [r for r in rows if not r['passed']]
    assert len(rejected) == 2 and all(r['type'] == 0 for r in rejected)
    assert all(max(map(abs, r['residual'])) > r['tolerance'] for r in rejected)
    assert audit['partial_initial']['would_reject_even_after_serialization_fix']
    assert not audit['partial_initial']['equality_values_independently_recomputed']
    return dict(setup_steps=500, task_steps=0, failure_audit_passed=True,
                partial_json_preserved=True, recorded_connect_rejections=len(rejected),
                model_reconstruction_performed=False, consumed_audit_budget=1,
                dynamics_validated=False)


def checks():
    rows = (REMOTE / 'job_status.txt').read_text().splitlines()
    expected = {'6858': 'COMPLETED|0:0', '6859': 'FAILED|1:0', '6860': 'COMPLETED|0:0'}
    for job, state in expected.items():
        assert any(row.startswith(job + '|' + state + '|') for row in rows)
    assert 'gres/gpu=1' in next(row for row in rows if row.startswith('6859|'))
    for path in ROOT.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= 300
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8')):
        assert (ROOT / target).is_file() or target == 'evidence/FINAL_VERIFICATION.json', target
    return expected


def main():
    lookup, counts = files()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
        files=counts, lineage=lineage(lookup), evidence=failure(lookup), jobs=checks(),
        model_calls=0, full_task_attempts=0, training_runs=0,
        retry_performed=False, production_gate_changed=False, review='serial_self_review')
    with (ROOT / 'evidence/FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert read(ROOT / 'evidence/FINAL_VERIFICATION.json') == result
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

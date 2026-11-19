"""仅复核已下载证据；不导入模型、仿真或真实执行入口。"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REMOTE = ROOT / 'evidence/remote'
PROJECT = ROOT.parent
SERVER = '/home/yeliheng/grasp_server/'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def archived(name):
    relative = name.removeprefix(SERVER)
    if relative.startswith('qualified_closure_dynamics_v1/'):
        return REMOTE / 'engine' / relative.removeprefix('qualified_closure_dynamics_v1/')
    return REMOTE / relative.removeprefix('qualified_closure_dynamics_run_v1/')


def files():
    delivery = read(ROOT / 'evidence/DELIVERY.json')
    matches = 0
    for row in delivery['files']:
        assert sha(REMOTE / row['name']) == row['sha256'], row['name']
        local = ROOT / row['name']
        if local.is_file():
            assert sha(local) == row['sha256'], row['name']
            matches += 1
    assert sorted(delivery['checks']['engine_run_files']) == ['claim.json', 'failure.json']
    return dict(downloaded=len(delivery['files']), local_source_matches=matches)


def evidence():
    auth = read(REMOTE / 'engine/authorization.json')
    claim = read(REMOTE / 'engine/run/claim.json')
    failure = read(REMOTE / 'engine/run/failure.json')
    audit = read(REMOTE / 'failure_audit.json')
    prepared = PROJECT / 'qualified_closure_dynamics_v1/evidence/remote/preparation_manifest.json'
    assert auth['preparation_sha256'] == sha(prepared)
    assert auth['identities'] == read(prepared)['identities']
    assert claim['consumed'] == 1 and claim['job'] == '6832'
    assert claim['authorization_sha256'] == sha(REMOTE / 'engine/authorization.json')
    assert failure['setup_step_requests'] == failure['task_step_requests'] == 0
    assert audit['passed'] and not audit['dynamics_validated']
    assert audit['scope'] == 'pre_scene_failure_evidence_only'
    assert audit['audit_integration_steps'] == 0 and audit['no_simulation_imported']
    for name, digest in audit['identities'].items():
        assert sha(archived(name)) == digest, name
    assert sha(ROOT / 'failure_audit.py') == audit['audit_source_sha256']
    assert audit['provenance']['installed_record_matches']
    assert not audit['historical_dependency_hash_bound']
    for name, digest in read(prepared)['sources'].items():
        assert sha(PROJECT / 'qualified_closure_dynamics_v1' / name) == digest
    return dict(frozen_identities=len(auth['identities']), implementation_unchanged=True,
                consumed_claim=1, setup_steps=0, task_steps=0, audit_steps=0,
                failure_evidence_audit_passed=True, dynamics_validated=False)


def jobs():
    data = (REMOTE / 'job_status.txt').read_text()
    expected = {'6831': 'COMPLETED|0:0', '6832': 'FAILED|1:0', '6833': 'COMPLETED|0:0'}
    for job, state in expected.items():
        assert job + '|' + state + '|' in data
    assert 'Unbound runtime source' in (REMOTE / 'execute-6832.log').read_text()
    return expected


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
                  files=files(), evidence=evidence(), jobs=jobs(), model_calls=0,
                  training_runs=0, production_gate_changed=False, retry_performed=False)
    with (ROOT / 'evidence/FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

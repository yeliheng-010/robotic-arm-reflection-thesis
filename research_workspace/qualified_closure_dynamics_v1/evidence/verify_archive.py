"""本地档案复核；不导入仿真或执行器、不运行实验。"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parent
PROJECT = ROOT.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def verify_files():
    delivery = read(EVIDENCE / 'DELIVERY.json')
    matches = 0
    for row in delivery['files']:
        remote = EVIDENCE / 'remote' / row['name']
        assert row['sha256'] == sha(remote), row['name']
        if row['name'].startswith('pre_oom_source/'):
            local = EVIDENCE / row['name']
        else:
            local = ROOT / row['name']
        if local.is_file():
            assert row['sha256'] == sha(local), row['name']
            matches += 1
    assert delivery['checks']['authorization_http'] == 404
    assert delivery['checks']['run_http'] == 404
    return dict(downloaded=len(delivery['files']), local_source_matches=matches)


def verify_manifest():
    remote = EVIDENCE / 'remote'
    manifest = read(remote / 'preparation_manifest.json')
    prior = read(PROJECT / 'qualified_closure_reachability_v1/evidence/remote/run/manifest.json')
    assert manifest['execution_authorized'] is False
    assert manifest['setup_steps'] == manifest['task_steps'] == 0
    for name, digest in prior['identities'].items():
        assert manifest['identities'][name] == digest, name
    for name, digest in manifest['sources'].items():
        assert sha(ROOT / name) == digest, name
    plan = PROJECT / 'qualified_closure_dynamics_plan_v1'
    original = read(plan / 'evidence/PLAN_VERIFICATION.json')
    for name, digest in original['artifacts'].items():
        assert sha(plan / name) == digest, name
    return dict(prepared_identities=len(manifest['identities']),
                preserved_prior_identities=len(prior['identities']),
                prepared_python_sources=len(manifest['sources']), prior_plan_unchanged=True)


def verify_jobs():
    remote = EVIDENCE / 'remote'
    status = (remote / 'job_status.txt').read_text()
    expected = {'6827': 'FAILED|1:0', '6828': 'OUT_OF_MEMORY|0:125',
                '6829': 'FAILED|1:0', '6830': 'COMPLETED|0:0'}
    for job, outcome in expected.items():
        assert job + '|' + outcome + '|' in status
    log = (remote / 'verify-6830.log').read_text()
    assert 'Ran 21 tests' in log and '\nOK\n' in log
    assert "'real_integration_or_scene_requests': 0" in log
    assert "'identities': 1332" in log
    assert 'Unbounded whole-file read' in (remote / 'hash-red-6829.log').read_text()
    assert (EVIDENCE / 'pre_oom_source/protocol.py').read_bytes() != (ROOT / 'protocol.py').read_bytes()
    return dict(jobs=expected, final_tests=21, actual_integration_steps=0,
                real_scene_requests=0, failures_preserved=True)


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
                  files=verify_files(), sources=verify_manifest(), validation=verify_jobs(),
                  dynamics_executed=False, runtime_initial_state_validated=False,
                  production_gate_changed=False, model_calls=0, training_runs=0)
    with (EVIDENCE / 'FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

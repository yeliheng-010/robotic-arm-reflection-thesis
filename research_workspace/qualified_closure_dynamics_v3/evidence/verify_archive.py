"""本地只校验归档、来源关系与记录，不导入仿真或执行测试。"""
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT, REMOTE = EVIDENCE.parent, EVIDENCE / 'remote'
PROJECT = ROOT.parent
SERVER = '/home/yeliheng/grasp_server/'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def local_source(name):
    version, relative = name.split('/', 1)
    root = PROJECT / ('qualified_closure_dynamics_' + version)
    if relative.startswith(('pre_virtual_fix/', 'pre_alias_fix/')):
        return root / 'evidence' / relative
    if relative == 'preflight_before_supplement.py':
        return root / 'evidence' / relative
    return root / relative


def check_downloads():
    delivery = read(EVIDENCE / 'DELIVERY.json')
    matches = 0
    for row in delivery['files']:
        assert sha(REMOTE / row['name']) == row['sha256'], row['name']
        local = local_source(row['name'])
        if local.is_file():
            assert sha(local) == row['sha256'], row['name']
            matches += 1
    for version in ('v2', 'v3'):
        assert delivery['checks'][version + '/authorization.json'] == 404
        assert delivery['checks'][version + '/run'] == 404
    assert delivery['checks']['old_claim']['consumed'] == 1
    assert delivery['checks']['old_claim']['job'] == '6832'
    return dict(downloaded=len(delivery['files']), local_source_matches=matches)


def check_lineage():
    v1 = read(PROJECT / 'qualified_closure_dynamics_v1/evidence/remote/preparation_manifest.json')
    v2 = read(REMOTE / 'v2/prepared/manifest.json')
    v3 = read(REMOTE / 'v3/prepared/manifest.json')
    for parent, child in ((v1, v2), (v2, v3)):
        for name, digest in parent['identities'].items():
            assert child['identities'][name] == digest, name
    sources = list(ROOT.glob('*.py'))
    for path in sources:
        assert v3['identities'][SERVER + 'qualified_closure_dynamics_v3/' + path.name] == sha(path)
    reviewed = read(ROOT / 'reviewed_sources.json')
    assert reviewed['reviewed'] and len(reviewed['identities']) == 15
    for name, digest in reviewed['identities'].items():
        assert sha(PROJECT / name.removeprefix(SERVER)) == digest
        assert v3['identities'][name] == digest
    claim = PROJECT / 'qualified_closure_dynamics_run_v1/evidence/remote/engine/run/claim.json'
    assert v3['identities'][SERVER + 'qualified_closure_dynamics_v1/run/claim.json'] == sha(claim)
    return dict(v1_identities=len(v1['identities']), v2_identities=len(v2['identities']),
                v3_identities=len(v3['identities']), final_python_sources=len(sources),
                newly_reviewed_project_files=15, old_claim_identity_preserved=True)


def check_runtime():
    manifest = read(REMOTE / 'v3/prepared/manifest.json')
    audit = read(REMOTE / 'v3/prepared/audit_result.json')
    snapshot_path = REMOTE / 'v3/prepared/runtime.json.gz'
    assert manifest['runtime_sha256'] == sha(snapshot_path)
    with gzip.open(snapshot_path, 'rt', encoding='utf-8') as stream:
        runtime = json.load(stream)
    assert audit['passed'] and audit['scope'] == 'real_imports_zero_motion'
    assert audit['preparation_sha256'] == sha(REMOTE / 'v3/prepared/manifest.json')
    assert not any(manifest['import_counts'].values()) and not any(audit['counts'].values())
    assert not audit['execution_authorized'] and not audit['dynamics_validated']
    assert len(runtime['files']) == manifest['files'] == 7188
    assert len(runtime['modules']) == manifest['modules'] == 4191
    assert len(runtime['distributions']['packages']) == manifest['packages'] == 62
    assert runtime['allowed_entrypoints'][audit['entrypoint']['file']] == audit['entrypoint']['sha256']
    assert '__mp_main__' not in runtime['modules']
    assert audit['regression_dependency']['source']['category'] == 'dependency'
    assert audit['regression_dependency']['owner']['installed_record']['matches']
    return dict(registered_modules=manifest['modules'], registered_files=manifest['files'],
                registered_packages=manifest['packages'], audited_modules=audit['modules'],
                audited_files=audit['files'], categories=dict(Counter(r['category'] for r in runtime['files'].values())),
                virtual_kinds=dict(Counter(r['kind'] for r in runtime['modules'].values())),
                all_8380_identities_verified_by_server=True, all_construction_and_integration_counts_zero=True)


def check_jobs():
    text = (REMOTE / 'v3/job_status.txt').read_text()
    failed = {'6834', '6836', '6838', '6840', '6842', '6845', '6846'}
    for number in range(6834, 6850):
        job = str(number)
        state = 'FAILED|1:0' if job in failed else 'COMPLETED|0:0'
        assert job + '|' + state + '|' in text
    final = (REMOTE / 'v3/test-6847.log').read_text()
    assert 'Ran 28 tests' in final and '\nOK\n' in final
    assert '__mp_main__' in (REMOTE / 'v2/audit-6845.log').read_text()
    return dict(final_tests=28, final_test_job='6847', preparation_job='6848', audit_job='6849',
                retained_failed_jobs=sorted(failed), old_experiments_repeated=False)


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
                  files=check_downloads(), lineage=check_lineage(), runtime=check_runtime(),
                  jobs=check_jobs(), new_dynamics_authorized=False, model_calls=0,
                  training_runs=0, physics_steps=0, production_gate_changed=False)
    with (EVIDENCE / 'FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

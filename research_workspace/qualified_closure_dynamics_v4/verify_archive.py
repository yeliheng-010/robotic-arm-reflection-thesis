"""本地档案核验，不导入仿真或执行实验。"""
import ast
import gzip
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
    matches = 0
    for row in delivery['files']:
        assert sha(REMOTE / row['name']) == row['sha256'], row['name']
        local = ROOT / row['name']
        if local.is_file():
            assert sha(local) == row['sha256'], row['name']
            matches += 1
    checks = delivery['checks']
    for name in ('v4_authorization', 'v4_run', 'v3_run'):
        assert checks[name] == 404, name
    previous = PROJECT / 'qualified_closure_dynamics_run_v3/evidence/remote/engine/authorization.json'
    assert sha(previous) == checks['v3_authorization_sha256']
    prior = PROJECT / 'qualified_closure_dynamics_run_v1/evidence/remote/engine/run/claim.json'
    assert sha(prior) == sha(REMOTE / 'history/v1_claim.json')
    assert read(prior)['consumed'] == 1
    return dict(downloaded=len(delivery['files']), local_source_matches=matches,
                new_authorization_and_run_absent=True, old_claim_and_authorization_preserved=True)


def lineage():
    manifest = read(REMOTE / 'prepared/manifest.json')
    previous = PROJECT / 'qualified_closure_dynamics_v3/evidence/remote/v3/prepared/manifest.json'
    prior = read(previous)
    for name, digest in prior['identities'].items():
        assert manifest['identities'][name] == digest, name
    assert manifest['identities'][SERVER + 'qualified_closure_dynamics_v3/prepared/manifest.json'] == sha(previous)
    matched = []
    for name, digest in manifest['identities'].items():
        relative = name.removeprefix(SERVER)
        if not relative.startswith('qualified_closure_dynamics_v4/'):
            continue
        path = REMOTE / relative.removeprefix('qualified_closure_dynamics_v4/')
        assert sha(path) == digest, path
        matched.append(path.name)
    assert sha(REMOTE / 'prepared/runtime.json.gz') == manifest['runtime_sha256']
    assert manifest['execution_authorized'] is False and not any(manifest['import_counts'].values())
    return dict(prior_identities=len(prior['identities']), new_identities=len(manifest['identities']),
                v4_bound_artifacts=len(matched), old_identities_preserved=True)


def runtime():
    manifest = read(REMOTE / 'prepared/manifest.json')
    with gzip.open(REMOTE / 'prepared/runtime.json.gz', 'rt', encoding='utf-8') as stream:
        snapshot = json.load(stream)
    profile = manifest['gpu_profile']
    assert profile == snapshot['gpu_profile']
    assert profile['gpu_allocated'] and profile['open3d_backend'] == 'cuda'
    assert profile['torch_devices'] == profile['open3d_devices'] == 1
    rejected = '/home/yeliheng/grasp_server/env_sim/lib/python3.11/site-packages/open3d/cuda/pybind.cpython-311-x86_64-linux-gnu.so'
    old_audit = read(PROJECT / 'qualified_closure_dynamics_run_v3/evidence/remote/failure_audit.json')
    assert snapshot['files'][rejected]['sha256'] == old_audit['dependency']['rejected_sha256']
    assert manifest['identities'][rejected] == snapshot['files'][rejected]['sha256']
    assert snapshot['distributions']['files'][rejected]['installed_record']['matches']
    results = {}
    for name, entry in (('audit_result.json', 'audit_imports.py'), ('entry_check.json', 'entry.py')):
        result = read(REMOTE / 'prepared' / name)
        assert result['passed'] and not result['execution_authorized'] and not result['dynamics_validated']
        assert not any(result['counts'].values()) and result['gpu_profile'] == profile
        assert result['verified_identities'] == len(manifest['identities'])
        assert result['preparation_sha256'] == sha(REMOTE / 'prepared/manifest.json')
        assert result['entrypoint']['file'] == SERVER + 'qualified_closure_dynamics_v4/' + entry
        assert result['entrypoint']['sha256'] == sha(ROOT / entry)
        results[name] = dict(job=result['job'], modules=result['modules'], files=result['files'])
    assert read(REMOTE / 'prepared/entry_check.json')['claim_consumed'] == 0
    return dict(gpu_profile=profile, modules=manifest['modules'], files=manifest['files'],
        packages=manifest['packages'], former_cuda_rejection_now_bound=True,
        all_construction_and_integration_counts_zero=True, independent_checks=results)


def sources():
    names = ['protocol.py', 'runtime.py', 'preflight.py', 'audit_imports.py', 'entry.py', 'test_gpu_entry.py']
    for name in names:
        source = (ROOT / name).read_text(encoding='utf-8')
        assert len(source.splitlines()) <= 300
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
    def body(version):
        tree = ast.parse((PROJECT / version / 'entry.py').read_text(encoding='utf-8'))
        return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_environment'))
    assert body('qualified_closure_dynamics_v3') == body('qualified_closure_dynamics_v4')
    directives = []
    for name in ('preflight.sbatch', 'audit.sbatch', 'entry_check.sbatch'):
        source = (ROOT / name).read_text()
        directives.append([line for line in source.splitlines() if line.startswith('#SBATCH')
                           and not any(key in line for key in ('job-name', 'output'))])
    assert directives[0] == directives[1] == directives[2]
    assert '--verify-imports' in (ROOT / 'entry_check.sbatch').read_text()
    return dict(frozen_python_sources=len(names), environment_function_ast_unchanged=True,
                gpu_slurm_resources_identical=True, review='serial_self_review')


def jobs():
    rows = (REMOTE / 'job_status.txt').read_text().splitlines()
    expected = {'6853': 'FAILED|1:0', '6854': 'COMPLETED|0:0', '6855': 'COMPLETED|0:0',
                '6856': 'COMPLETED|0:0', '6857': 'COMPLETED|0:0'}
    for job, state in expected.items():
        row = next(row for row in rows if row.startswith(job + '|'))
        assert row.startswith(job + '|' + state + '|'), row
        if job in ('6855', '6856', '6857'):
            assert 'gres/gpu=1' in row and 'mem=16G' in row
    assert 'Ran 7 tests' in (REMOTE / 'tests-6854.log').read_text()
    assert 'OK' in (REMOTE / 'tests-6854.log').read_text()
    return expected


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
        files=files(), lineage=lineage(), runtime=runtime(), sources=sources(), jobs=jobs(),
        new_dynamics_authorized=False, model_calls=0, training_runs=0, dynamics_validated=False,
        old_experiments_repeated=False, production_gate_changed=False)
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8')):
        assert (ROOT / target).is_file() or target == 'evidence/FINAL_VERIFICATION.json', target
    with (ROOT / 'evidence/FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert read(ROOT / 'evidence/FINAL_VERIFICATION.json') == result
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

"""本地只验证归档字节、源码及服务端验证记录。"""
import ast
import hashlib
import json
import re
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT, REMOTE = EVIDENCE.parent, EVIDENCE/'remote'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_files(delivery):
    matched = []
    for row in delivery['files']:
        relative = Path(row['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        path = REMOTE/relative
        assert path.stat().st_size == row['size'] and sha(path) == row['sha256'], row['path']
        if len(relative.parts) == 1 and (ROOT/relative).is_file():
            assert sha(ROOT/relative) == row['sha256'], row['path']
            matched.append(row['path'])
    for name, digest in read(REMOTE/'verification/primary_inventory.json').items():
        assert sha(REMOTE/'verification'/name) == digest, name
    return matched


def check_tests():
    expected = {'6883': (22, 22), '6884': (28, 0), '6885': (3, 2), '6886': (30, 0)}
    for job, (tests, failures) in expected.items():
        result = read(REMOTE/f'tests_{job}.json')
        assert result['tests'] == tests and result['failures'] == failures and result['errors'] == 0
        assert not any(result['counts'].values())
    green = read(REMOTE/'tests_6886.json')
    assert green['passed']
    actual = {p.name: sha(p) for p in ROOT.glob('*.py')}
    assert green['source_hashes'] == actual
    selected = read(REMOTE/'TEST_RESULT.json')
    assert selected['sha256'] == sha(REMOTE/selected['path'])
    return dict(final_tests=green['tests'], tested_python_sources=len(actual))


def check_result():
    prepared = read(REMOTE/'prepared/manifest.json')
    entry, audit = [read(REMOTE/'verification'/p) for p in ('result.json', 'audit_result.json')]
    ready = read(REMOTE/'readiness.json')
    assert prepared['passed'] and not any(prepared['counts'].values())
    assert entry['reasons'] == ['verification_only'] and entry['completed_steps'] == 0
    assert entry['error'] is None and entry['observed_steps'] == 0 and entry['uncertain_step'] is None
    assert audit['passed'] and audit['scope'] == 'full_trace' and audit['verification_only']
    assert ready['entrypoint_ready'] and not ready['execution_authorized'] and ready['dynamics_budget_consumed'] == 0
    for result in (entry, audit):
        assert not any(result['import_counts'].values())
        assert result['counts']['binary_load'] == 1
        assert all(result['counts'][k] == 0 for k in ('integration', 'native_returns', 'setup_steps',
                   'reset', 'compile', 'rendering', 'close', 'planning', 'optimizer', 'forbidden'))
    assert entry['counts']['live_forward'] == entry['counts']['copy_forward'] == 1
    assert audit['counts']['live_forward'] == 0 and audit['counts']['copy_forward'] == 1
    for name in ('authorization.json', 'execute.sbatch', 'run'):
        assert not (ROOT/name).exists() and not (REMOTE/name).exists()
    return dict(preparation_job=prepared['job'], entry_job=entry['job'], audit_job=audit['job'],
                readiness_job=ready['job'], source_identities=entry['verified_identities'])


def check_source_and_report():
    for path in ROOT.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        lengths = [n.end_lineno-n.lineno+1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert len(source.splitlines()) <= 300 and max(lengths, default=0) <= 50, path.name
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT/'REPORT.md').read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'):
            continue
        path = (ROOT/target).resolve()
        if path != (EVIDENCE/'FINAL_VERIFICATION.json').resolve():
            assert path.exists(), target


def main():
    delivery = read(EVIDENCE/'DELIVERY.json')
    matched = check_files(delivery)
    result = dict(**check_tests(), **check_result())
    check_source_and_report()
    result.update(passed=True, files_verified=len(delivery['files']), matched_local_files=matched,
                  entrypoint_ready=True, execution_authorized=False, dynamics_validated=False,
                  production_ready=False, simulator_run_locally=False, remote_only=delivery['remote_only'])
    path = EVIDENCE/'FINAL_VERIFICATION.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assert read(path) == result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

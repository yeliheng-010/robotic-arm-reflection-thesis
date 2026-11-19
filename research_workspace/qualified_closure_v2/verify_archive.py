"""仅复算本地证据哈希、统计和链接；不运行仿真或模型。"""
import ast
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
REMOTE = EVIDENCE / 'remote'
RUN = REMOTE / 'qualified_closure_v2/run'
OUTPUT = EVIDENCE / 'FINAL_VERIFICATION.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_source(local, remote, row):
    assert sha(local) == row['local_utf8_sha256']
    assert sha(remote) == row['executed_sha256']
    if row['byte_exact']:
        assert local.read_bytes() == remote.read_bytes()
        return 'byte_exact'
    first, second = local.read_text(encoding='utf-8'), remote.read_text(encoding='utf-8')
    assert first.encode('gbk', errors='replace').decode('utf-8', errors='replace') == second
    if local.suffix == '.md':
        return 'non_executable_plan_encoding'
    assert local.suffix == '.py'
    a, b = ast.parse(first), ast.parse(second)
    for tree in (a, b):
        assert isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant)
        assert isinstance(tree.body[0].value.value, str)
        tree.body = tree.body[1:]
    assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)
    return 'module_docstring_only_runtime_ast_exact'


def files():
    downloaded = read(EVIDENCE / 'DELIVERY.json')['files']
    reconciled = {row['path']: row for row in read(EVIDENCE / 'UTF8_SOURCE_RECONCILIATION.json')['files']}
    corrected = {row['path']: row['sha256'] for row in read(EVIDENCE / 'UTF8_SNAPSHOT_VERIFICATION.json')['files']}
    seen, sources = set(), {}
    for row in downloaded:
        assert row['path'] not in seen
        seen.add(row['path'])
        remote = (REMOTE / row['path']).resolve()
        assert remote.is_relative_to(REMOTE.resolve())
        assert sha(remote) == row['sha256'], row['path']
        parts = Path(row['path']).parts
        if len(parts) == 2 and remote.suffix in ('.py', '.sbatch', '.md'):
            local = ROOT.parent / row['path']
            category = compare_source(local, remote, reconciled[row['path']])
            assert sha(local) == corrected[row['path']]
            sources[category] = sources.get(category, 0) + 1
    inventory = read(RUN / 'delivery_inventory.json')
    for name, digest in inventory['identities'].items():
        assert sha(REMOTE / name) == digest, name
    assert inventory['passed'] and inventory['original_exact_audit_passed'] is False
    return dict(downloaded=len(seen), source_comparison=sources,
                corrected_utf8_snapshot_files=len(corrected), frozen_inventory=len(inventory['identities']))


def stats():
    closure = read(RUN / 'closure.json')
    valid = [row for row in closure['envelope'] if row['valid']]
    collisions = [row for row in valid if row['contacts']]
    assert not closure['passed'] and all(row['valid'] for row in closure['rows'])
    assert len(valid) == closure['envelope_valid'] == 283
    assert len(collisions) == closure['envelope_collisions'] == 90
    assert len(closure['envelope']) == 697
    assert not any(row['contacts'] for row in closure['rows'])
    assert all(c['roots'] == ['SortingTray', '2f85_base'] for row in collisions for c in row['contacts'])
    audit = read(RUN / 'audit.json')
    assert audit['passed'] and audit['original_samples_exact']
    assert audit['dense_samples'] == audit['dense_valid'] == 161
    assert audit['dense_collisions'] == audit['integration']['physical_close_calls'] == 0
    safe = read(RUN / 'safe_home_test/closure_precheck.json')
    assert safe['passed'] and safe['envelope_collisions'] == 0
    assert read(RUN / 'positive.json')['guarded_original_sentinel_calls'] == 1
    for folder in ('restored_terminal', 'synthetic_stale_cache', 'integration_test/terminal_evaluation'):
        result = read(RUN / folder / 'evaluation.json')
        for name, digest in result['identities'].items():
            assert sha(RUN / folder / name) == digest, (folder, name)
        if folder != 'restored_terminal':
            offset = result['cached']['evaluation']['position'][0] - result['rebuilt']['evaluation']['position'][0]
            assert math.isclose(offset, 1e-4, rel_tol=0, abs_tol=1e-12)
            assert not result['cross_timing_identical']
    return dict(nominal_samples=len(closure['rows']), valid_envelope=len(valid),
                colliding_envelope=len(collisions), safe_home_passed=True,
                independent_audit_passed=True, physical_close_calls=0)


def sources():
    paths = list(ROOT.glob('*.py')) + list((ROOT.parent / 'qualified_closure_v1').glob('*.py'))
    for path in paths:
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path.name, node.name)
    return len(paths)


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), files=files(),
                  stats=stats(), local_python_sources_checked=sources(),
                  verifier_sha256=sha(Path(__file__)), physical_attempts_added=0,
                  model_calls_added=0, training_runs_added=0)
    report = ROOT / 'REPORT.md'
    targets = [(ROOT / value).resolve() for value in re.findall(r'\[[^\]]*\]\(([^)]+)\)',
                                                               report.read_text(encoding='utf-8'))]
    for target in targets:
        assert target.is_file() or target == OUTPUT.resolve(), target
    result['report_links_checked'] = len(targets)
    log = (REMOTE / 'qualified_closure_v2/closeout-6802.log').read_text(encoding='utf-8')
    assert 'Ran 17 tests' in log and '\nOK\n' in log
    result['server_regression_tests'] = 17
    result['pending_current_scope'] = []
    if '--write' in sys.argv:
        with OUTPUT.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    assert OUTPUT.is_file()
    for target in targets:
        assert target.is_file(), target
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

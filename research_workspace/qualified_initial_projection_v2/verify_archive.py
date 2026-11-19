"""只复核本地档案与来源，不执行优化或数值测试。"""
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
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def files():
    delivery = read(ROOT / 'evidence/DELIVERY.json')
    lookup, matches = {}, 0
    for row in delivery['files']:
        path = REMOTE / row['name']
        assert path.resolve().is_relative_to(REMOTE.resolve())
        assert sha(path) == row['sha256'] and path.stat().st_size == row['size']
        lookup[row['remote']] = path
        local = PROJECT / row['remote']
        if local.is_file():
            assert sha(local) == row['sha256'], row['remote']
            matches += 1
    for key in ('run', 'authorization', 'failure', 'old_candidate'):
        assert delivery['checks'][key] == 404
    return lookup, dict(downloaded=len(delivery['files']), local_matches=matches)


def lineage(lookup):
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        assert sha(lookup[name]) == digest, name
    manifest = read(REMOTE / 'inputs/parent_manifest.json')['identities']
    assert len(manifest) == 8448
    parent = PROJECT / 'qualified_initial_projection_v1/evidence/remote'
    for name, old in [('parent_manifest.json', 'prepared/manifest.json'), ('old_result.json', 'run/result.json'),
                      ('v4_claim.json', 'inputs/v4_claim.json'), ('v4_failure.json', 'inputs/v4_failure.json'),
                      ('initial_transform.npz', 'inputs/initial_transform.npz')]:
        assert sha(REMOTE / 'inputs' / name) == sha(parent / old), name
    diagnostic = PROJECT / 'qualified_projection_diagnostic_v1/evidence/remote'
    assert sha(REMOTE / 'inputs/diagnostic_result.json') == sha(diagnostic / 'run/result.json')
    assert read(REMOTE / 'inputs/v4_claim.json')['consumed'] == 1
    assert not read(REMOTE / 'inputs/old_result.json')['candidate_created']
    loaded = read(REMOTE / 'prepared/loaded_sources.json')
    for name, digest in loaded.items():
        assert manifest[name] == digest, name
    for name, digest in read(REMOTE / 'prepared/inventory.json').items():
        assert sha(REMOTE / 'prepared' / name) == digest, name
    return dict(identities=8448, loaded_numerical_files=len(loaded), old_evidence_preserved=True)


def results():
    result = read(REMOTE / 'prepared/result.json')
    assert result['passed'] and result['tests']['passed'] == 12
    assert result['verified_identities'] == 8448 and result['tests']['actual_optimizer_runs'] == 0
    assert not any(result['optimizer_counts'].values()) and not any(result['motion_counts'].values())
    for key in ('real_solver_convergence_validated', 'execution_authorized', 'candidate_created', 'production_ready'):
        assert not result[key], key
    for rows in result['fixed_points'].values():
        assert [row['label'] for row in rows] == ['original', 'clipped', 'saved_attempt']
        for row in rows:
            assert row['jacobian_difference_max'] <= 1e-7
            assert not row['geometry_search_performed']
    assert read(REMOTE / 'prepared/validation_claim.json') == dict(
        consumed=1, job='6873', optimizer_budget=0, integration_budget=0)
    jobs = (REMOTE / 'job_status.txt').read_text()
    assert '6872|FAILED|1:0|' in jobs and '6873|COMPLETED|0:0|' in jobs
    red = (REMOTE / 'red-6872.log').read_text()
    green = (REMOTE / 'preflight-6873.log').read_text()
    assert 'Constraint Jacobian must be explicitly supplied' in red and 'FAILED (failures=1)' in red
    assert 'Ran 12 tests' in green and '\nOK\n' in green
    assert not (REMOTE / 'queue_status.txt').read_text().strip()
    return dict(tests_passed=12, fixed_points=6, actual_optimizer_calls=0, integration_calls=0, queue_empty=True)


def sources_and_rules():
    bound = read(ROOT / 'BINDINGS.json')
    count = 0
    for path in ROOT.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno-node.lineno+1 <= 50, node.name
        name = ROOT.name + '/' + path.name
        if name in bound:
            assert sha(path) == bound[name]
            count += 1
    assert count == 6
    rules = read(ROOT / 'NEXT_RUN_RULES.json')
    assert not rules['execution_authorized'] and not rules['entrypoint_ready']
    assert rules['algorithm_bindings_sha256'] == sha(ROOT / 'BINDINGS.json')
    assert rules['preflight_result_sha256'] == sha(REMOTE / 'prepared/result.json')
    assert rules['source_state_sha256'] == sha(REMOTE / 'inputs/initial_transform.npz')
    future = rules['future_run']
    assert future['attempts_per_side'] == 1 and future['optimizer_success_required']
    assert future['ftol'] == 1e-14 and future['max_iterations_per_side'] == 200
    assert future['full_3d_connect_tolerance_m'] == 1e-7 and future['passive_change_cap_rad'] == 0.01
    assert not (ROOT / 'run').exists() and not (ROOT / 'authorization.json').exists()
    return dict(frozen_python_sources=count, next_rules_sha256=sha(ROOT / 'NEXT_RUN_RULES.json'),
                new_execution_authorized=False, actual_convergence_validated=False)


def main():
    lookup, archived = files()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
        files=archived, lineage=lineage(lookup), results=results(), sources_and_rules=sources_and_rules(),
        review='serial_self_review', model_generations=0, training_runs=0)
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8')):
        assert (ROOT / target).is_file() or target == 'evidence/FINAL_VERIFICATION.json', target
    with (ROOT / 'evidence/FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert read(ROOT / 'evidence/FINAL_VERIFICATION.json') == result
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

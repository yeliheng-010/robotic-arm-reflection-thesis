"""只核验本地档案、源码和已保存字段，不运行数值计算。"""
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT, REMOTE = ROOT.parent, ROOT / 'evidence/remote'
SERVER = '/home/yeliheng/grasp_server/'
PARENT = PROJECT / 'qualified_initial_projection_v1/evidence/remote'


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
    lookup, local_matches = {}, 0
    for row in delivery['files']:
        target = REMOTE / row['name']
        assert target.resolve().is_relative_to(REMOTE.resolve())
        assert sha(target) == row['sha256'] and target.stat().st_size == row['size']
        lookup[row['remote']] = target
        local = PROJECT / row['remote']
        if local.is_file():
            assert sha(local) == row['sha256'], row['remote']
            local_matches += 1
    for key in ('parent_candidate', 'candidate', 'failure', 'authorization'):
        assert delivery['checks'][key] == 404
    for name in ('candidate_state.npz', 'failure.json'):
        assert not (REMOTE / 'run' / name).exists()
    return lookup, dict(downloaded=len(delivery['files']), local_matches=local_matches)


def lineage(lookup):
    bindings = read(ROOT / 'BINDINGS.json')
    for name, digest in bindings.items():
        assert name in lookup and sha(lookup[name]) == digest, name
    pairs = [('parent_manifest.json', 'prepared/manifest.json'), ('parent_result.json', 'run/result.json'),
             ('parent_audit.json', 'run/audit_result.json'), ('parent_inventory.json', 'run/inventory.json'),
             ('v4_claim.json', 'inputs/v4_claim.json'), ('v4_failure.json', 'inputs/v4_failure.json'),
             ('initial_transform.npz', 'inputs/initial_transform.npz')]
    for name, old in pairs:
        assert sha(REMOTE / 'inputs' / name) == sha(PARENT / old), name
    manifest = read(REMOTE / 'inputs/parent_manifest.json')['identities']
    assert len(manifest) == 8448
    for remote, path in lookup.items():
        if SERVER + remote in manifest:
            assert sha(path) == manifest[SERVER + remote], remote
    loaded = read(REMOTE / 'run/loaded_sources.json')
    assert loaded
    for name, digest in loaded.items():
        assert manifest[name] == digest, name
    for name, digest in read(REMOTE / 'run/inventory.json').items():
        assert sha(REMOTE / 'run' / name) == digest, name
    assert read(REMOTE / 'inputs/v4_claim.json')['consumed'] == 1
    return dict(identities=8448, bound_loaded_numerical_files=len(loaded), prior_evidence_unchanged=True)


def results():
    result = read(REMOTE / 'run/result.json')
    assert result['passed'] and result['job'] == '6871' and result['tests']['passed'] == 3
    assert result['verified_identities'] == 8448
    assert not any(result['optimizer_counts'].values()) and not any(result['motion_counts'].values())
    assert sha(REMOTE / 'inputs/parent_result.json') == result['original_result_sha256']
    old = read(REMOTE / 'inputs/parent_result.json')
    assert not old['candidate_created'] and old['solutions']['left']['status'] == 8
    geometry = result['geometry']
    assert geometry['saved_value_geometry_passed'] and geometry['driver_fixed']
    assert geometry['original_ranges_and_change_cap_passed'] and abs(geometry['driver_residual']) <= 1e-7
    assert geometry['original_rejection_preserved'] and not geometry['executable_state_created']
    for row in geometry['connections']:
        assert row['passed'] and row['max_world_abs'] <= 1e-7
    changes = {row['name']: row for row in geometry['changes']}
    for side in ('right', 'left'):
        for index, part in enumerate(('coupler', 'spring_link', 'follower')):
            row = changes[f'{side}_{part}_joint']
            assert row['saved'] == old['solutions'][side]['angles'][index]
            assert row['delta'] == old['solutions'][side]['delta'][index]
        numeric = result['numerics'][side]
        assert numeric['complex_cross_max_abs_error'] <= 1e-10
        assert numeric['three_point_max_abs_error'] <= 1e-6
        assert numeric['first_order']['upper_multiplier'] > 0
    for key in ('unique_failure_cause_proven', 'optimizer_success_reinterpreted', 'candidate_created',
                'full_scene_checked', 'dynamics_validated', 'production_ready', 'execution_authorized'):
        assert not result[key], key
    return dict(saved_geometry_passed=True, old_rejection_preserved=True, optimizer_calls=0,
                integration_calls=0, unique_failure_cause_proven=False, candidate_created=False)


def sources_and_jobs():
    bound = read(ROOT / 'BINDINGS.json')
    count = 0
    for path in ROOT.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
        name = ROOT.name + '/' + path.name
        if name in bound:
            assert sha(path) == bound[name]
            count += 1
    assert count == 4
    rows = (REMOTE / 'job_status.txt').read_text().splitlines()
    assert any(row.startswith('6871|COMPLETED|0:0|00:00:52|') for row in rows)
    assert not (REMOTE / 'queue_status.txt').read_text().strip()
    assert read(REMOTE / 'run/diagnostic_claim.json') == dict(
        consumed=1, job='6871', optimizer_budget=0, integration_budget=0)
    return dict(frozen_python_sources=count, job='6871 COMPLETED/0:0', queue_empty=True)


def main():
    lookup, archived = files()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
        files=archived, lineage=lineage(lookup), results=results(), sources_and_jobs=sources_and_jobs(),
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

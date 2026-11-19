"""复核归档及已保存状态数组；不运行模型、求解器或仿真。"""
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT, REMOTE = ROOT.parent, ROOT / 'evidence/remote'


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
    for key in ('failure', 'audit_failure', 'old_candidate', 'algorithm_run', 'algorithm_authorization'):
        assert delivery['checks'][key] == 404
    return lookup, dict(downloaded=len(delivery['files']), local_matches=matches)


def lineage(lookup):
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        assert sha(lookup[name]) == digest, name
    parent = PROJECT / 'qualified_initial_projection_v1/evidence/remote'
    for name, old in [('parent_manifest.json', 'prepared/manifest.json'), ('old_result.json', 'run/result.json'),
                      ('v4_claim.json', 'inputs/v4_claim.json'), ('v4_failure.json', 'inputs/v4_failure.json'),
                      ('initial_transform.npz', 'inputs/initial_transform.npz')]:
        assert sha(REMOTE / 'inputs' / name) == sha(parent / old), name
    algorithm = PROJECT / 'qualified_initial_projection_v2/evidence/remote'
    assert sha(REMOTE / 'inputs/algorithm_preflight.json') == sha(algorithm / 'prepared/result.json')
    manifest = read(REMOTE / 'inputs/parent_manifest.json')['identities']
    assert len(manifest) == 8448 and read(REMOTE / 'inputs/v4_claim.json')['consumed'] == 1
    assert not read(REMOTE / 'inputs/old_result.json')['candidate_created']
    loaded_sets = [read(REMOTE / 'prepared.json')['loaded_sources'],
                   read(REMOTE / 'run/loaded_sources.json'), read(REMOTE / 'run/audit_loaded_sources.json')]
    for loaded in loaded_sets:
        assert loaded
        for name, digest in loaded.items():
            assert manifest[name] == digest, name
    for name, digest in read(REMOTE / 'run/inventory.json').items():
        assert sha(REMOTE / 'run' / name) == digest, name
    return dict(identities=8448, loaded_file_counts=[len(x) for x in loaded_sets], old_evidence_preserved=True)


def budget():
    auth = read(REMOTE / 'authorization.json')
    expected = dict(sides=2, attempts_per_side=1, audits=1, initialization_steps=0,
                    integration_steps=0, model_generations=0, training_runs=0)
    assert auth['kind'] == 'isolated_geometry_only' and auth['geometry_execution_authorized']
    assert not auth['dynamics_execution_authorized'] and auth['budget'] == expected
    assert auth['bindings_sha256'] == sha(ROOT / 'BINDINGS.json')
    assert auth['prepared_sha256'] == sha(REMOTE / 'prepared.json')
    assert auth['rules_sha256'] == sha(ROOT / 'RULES.json')
    for name in ('construction', 'right', 'left', 'audit'):
        claim = read(REMOTE / 'run' / (name+'_claim.json'))
        assert claim['consumed'] == 1 and claim['integration_budget'] == 0 and claim['name'] == name
        assert claim['rules_sha256'] == auth['rules_sha256']
        assert claim['job'] == ('6876' if name == 'audit' else '6875')
    return dict(construction_claim=1, right_claim=1, left_claim=1, audit_claim=1, dynamics_authorized=False)


def results():
    result, audit = read(REMOTE / 'run/result.json'), read(REMOTE / 'run/audit_result.json')
    prepared = read(REMOTE / 'prepared.json')
    assert prepared['passed'] and prepared['tests_passed'] == 9
    assert not any(prepared['optimizer_counts'].values()) and not any(prepared['motion_counts'].values())
    assert result['candidate_created'] and result['geometry_feasible']
    assert audit['passed'] and audit['candidate_verified']
    assert not any(result['counts'].values()) and not any(audit['motion_counts'].values())
    assert not any(audit['optimizer_counts'].values())
    assert audit['allowed_counts'] == dict(isolated_model=1, data=2, forward=0, rendering=0)
    for item in (prepared, result, audit):
        assert item['verified_identities'] == 8448
    for item in (result, audit):
        assert not item['full_scene_checked'] and not item['production_ready'] and not item['dynamics_validated']
        assert item['state_contract']['other_state_unchanged']
        assert abs(item['state_contract']['driver_residual']) <= 1e-7
    for side, iterations in [('right', 48), ('left', 14)]:
        solved = result['solutions'][side]
        assert solved == read(REMOTE / 'run' / (side+'_result.json'))
        assert solved['accepted'] and solved['optimizer_success'] and solved['status'] == 0
        assert solved['actual_optimizer_calls'] == solved['attempts'] == 1
        assert solved['iterations'] == iterations and not solved['global_minimum_proven']
    for expected, actual in zip(result['connections'], audit['connections']):
        assert actual['passed'] and actual['maximum_abs'] <= 1e-7
        for frame in ('world', 'local'):
            np.testing.assert_allclose(expected[frame], actual[frame], atol=1e-12, rtol=0)
    assert sha(REMOTE / 'run/candidate_state.npz') == audit['candidate_sha256']
    return dict(candidate_verified=True, solver_calls=2, initialization_steps=0, integration_steps=0,
                isolated_audit_models=1, production_ready=False, candidate_sha256=audit['candidate_sha256'])


def saved_arrays():
    with np.load(REMOTE / 'run/candidate_state.npz', allow_pickle=False) as data:
        candidate, reference = data['integration'], data['reference']
    with np.load(REMOTE / 'inputs/initial_transform.npz', allow_pickle=False) as data:
        np.testing.assert_array_equal(data['after'], reference)
    parameters, result = read(REMOTE / 'inputs/parameters.json'), read(REMOTE / 'run/result.json')
    assert np.isfinite(candidate).all() and candidate.shape == reference.shape
    allowed = [1+row['qpos_address'] for row in parameters['joints'] if 'driver' not in row['name']]
    mask = np.ones(candidate.size, dtype=bool)
    mask[allowed] = False
    np.testing.assert_array_equal(reference[mask], candidate[mask])
    assert np.max(np.abs(candidate[allowed]-reference[allowed])) <= 0.01
    assert np.flatnonzero(candidate != reference).tolist() == allowed
    for row in parameters['joints']:
        value = candidate[1+row['qpos_address']]
        assert row['range'][0] <= value <= row['range'][1]
        side, part = row['name'].split('_', 1)
        part = part.removesuffix('_joint')
        if part != 'driver':
            assert value == result['solutions'][side]['angles'][('coupler', 'spring_link', 'follower').index(part)]
    return dict(reference_equals_old_after=True, other_state_unchanged=True, changed_indices=allowed)


def sources_jobs():
    bound, count = read(ROOT / 'BINDINGS.json'), 0
    for path in ROOT.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno-node.lineno+1 <= 50, node.name
        name = ROOT.name+'/'+path.name
        if name in bound:
            assert sha(path) == bound[name]
            count += 1
    assert count == 6
    jobs = (REMOTE / 'job_status.txt').read_text()
    for job in ('6874', '6875', '6876'):
        assert job+'|COMPLETED|0:0|' in jobs
    log = (REMOTE / 'prepare-6874.log').read_text()
    assert 'Ran 9 tests' in log and '\nOK\n' in log
    assert not (REMOTE / 'queue_status.txt').read_text().strip()
    algorithm = read(REMOTE / 'inputs/algorithm_bindings.json')
    for path in (REMOTE / 'algorithm').glob('*.py'):
        assert sha(path) == algorithm['qualified_initial_projection_v2/'+path.name]
    return dict(frozen_entry_python_sources=count, frozen_algorithm_python_sources=6, queue_empty=True)


def main():
    lookup, archived = files()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True, files=archived,
        lineage=lineage(lookup), budget=budget(), results=results(), saved_arrays=saved_arrays(),
        sources_jobs=sources_jobs(), review='serial_self_review', model_generations=0, training_runs=0)
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8')):
        assert (ROOT / target).is_file() or target == 'evidence/FINAL_VERIFICATION.json', target
    with (ROOT / 'evidence/FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert read(ROOT / 'evidence/FINAL_VERIFICATION.json') == result
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

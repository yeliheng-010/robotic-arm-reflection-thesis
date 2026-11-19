"""复核已下载档案和保存数值，不运行模型或仿真。"""
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

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
        target = REMOTE / row['name']
        assert sha(target) == row['sha256'], row['name']
        lookup[SERVER + row['remote']] = target
        local = PROJECT / row['remote']
        if local.is_file():
            assert sha(local) == row['sha256'], row['remote']
            matches += 1
    checks = delivery['checks']
    assert checks['new_authorization_status'] == 404
    old = PROJECT / 'qualified_closure_dynamics_run_v4/evidence/remote/engine'
    assert sha(old / 'authorization.json') == checks['v4_authorization_sha256']
    assert sha(old / 'run/claim.json') == sha(REMOTE / 'inputs/v4_claim.json')
    assert sha(old / 'run/initial.json') == sha(REMOTE / 'inputs/initial.json')
    return lookup, dict(downloaded=len(delivery['files']), local_source_matches=matches,
                        old_claim_and_partial_json_preserved=True, new_dynamics_authorization=False)


def lineage(lookup):
    manifest = read(REMOTE / 'prepared/manifest.json')
    old = read(PROJECT / 'qualified_closure_dynamics_run_v4/evidence/remote/engine/authorization.json')
    for name, digest in old['identities'].items():
        assert manifest['identities'][name] == digest, name
    for name, path in lookup.items():
        if name in manifest['identities']:
            assert sha(path) == manifest['identities'][name], name
    assert not manifest['execution_authorized'] and manifest['integration_budget'] == 0
    assert not any(manifest['import_counts'].values())
    for name, digest in read(REMOTE / 'run/inventory.json').items():
        assert sha(REMOTE / 'run' / name) == digest
    return dict(prior_identities=len(old['identities']), identities=len(manifest['identities']),
                old_identities_preserved=True)


def results():
    result, audit = read(REMOTE / 'run/result.json'), read(REMOTE / 'run/audit_result.json')
    assert result['passed'] and audit['passed']
    assert result['counts'] == dict(integration=0, scene=0, rendering=0, forbidden_model=0,
                                    forward=0, isolated_model=1, data=3)
    assert not any(audit['counts'].values())
    assert result['original_equals_before'] and result['fingers_unchanged']
    assert result['residual_preexists_placement'] and result['rigid_rotation_preserves_local_residual']
    assert not result['full_scene_reconstructed'] and not result['dynamics_validated']
    assert sha(REMOTE / 'run/result.json') == audit['result_sha256']
    assert sha(REMOTE / 'inputs/2f85.xml') == audit['source_xml_sha256']
    for item in (result, audit):
        assert item['imports']['verified_identities'] == 8427
        assert not any(item['imports']['import_counts'].values())
        assert not item['safety_gate_changed']
    for label in ('before', 'after'):
        for row, independent in zip(result['states'][label], audit['formula_rows'][label]):
            for frame in ('world', 'local'):
                np.testing.assert_allclose(row[frame], independent[frame], atol=1e-12, rtol=0)
            assert row['maximum_abs'] > 1e-7 and not row['passed']
    return dict(diagnostic_integration=0, audit_integration=0, isolated_model_count=1,
                full_scene_created=False, independent_formula_passed=True,
                residual_preexists_placement=True, dynamics_validated=False)


def saved_values():
    parameters = read(REMOTE / 'inputs/parameters.json')
    with np.load(REMOTE / 'inputs/initial_transform.npz', allow_pickle=False) as data:
        before, after = data['before'], data['after']
    with np.load(REMOTE / 'inputs/source_state.npz', allow_pickle=False) as data:
        np.testing.assert_array_equal(data['state'], before)
    flags, outside = [], []
    for row in parameters['joints']:
        address = 1 + row['qpos_address']
        assert before[address] == after[address]
        value = float(after[address])
        valid = row['range'][0] <= value <= row['range'][1]
        flags.append(valid)
        if not valid:
            outside.append(dict(name=row['name'], value_rad=value, range=row['range']))
    assert flags == read(REMOTE / 'run/result.json')['finger_limits']
    subset = read(REMOTE / 'run/reconstructed_report_subset.json')
    assert subset['finger_limits'] == flags and not subset['replaces_original']
    assert len(outside) == 2
    return dict(original_snapshot_equals_before=True, fingers_unchanged=True, outside_limits=outside)


def sources():
    old = (REMOTE / 'inputs/legacy_initial.py').read_text(encoding='utf-8')
    new = (ROOT / 'initial.py').read_text(encoding='utf-8')
    fixed = "bool(row['range'][0] <= data.qpos[row['qpos_address']] <= row['range'][1])"
    original = "row['range'][0] <= data.qpos[row['qpos_address']] <= row['range'][1]"
    assert new.replace(fixed, original) == old
    manifest = read(REMOTE / 'prepared/manifest.json')
    count = 0
    for path in ROOT.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
        remote = SERVER + 'qualified_initial_state_v1/' + path.name
        if remote in manifest['identities']:
            assert sha(path) == manifest['identities'][remote]
            count += 1
    return dict(frozen_python_sources=count, only_initial_change_is_bool_conversion=True,
                review='serial_self_review')


def jobs():
    rows = (REMOTE / 'job_status.txt').read_text().splitlines()
    expected = {'6861': 'FAILED|1:0', '6862': 'COMPLETED|0:0', '6863': 'COMPLETED|0:0',
                '6864': 'COMPLETED|0:0', '6865': 'COMPLETED|0:0'}
    for job, state in expected.items():
        assert any(row.startswith(job + '|' + state + '|') for row in rows)
    assert 'FAILED (errors=3)' in (REMOTE / 'tests-6861.log').read_text()
    assert 'Ran 3 tests' in (REMOTE / 'tests-6862.log').read_text()
    assert 'OK' in (REMOTE / 'tests-6862.log').read_text()
    return expected


def main():
    lookup, archived = files()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
        files=archived, lineage=lineage(lookup), results=results(), saved_values=saved_values(),
        sources=sources(), jobs=jobs(), model_generations=0, training_runs=0,
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

"""只复核本地档案、保存的结果和来源；不导入数值或仿真库。"""
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
REMOTE = ROOT / 'evidence/remote'
SERVER = '/home/yeliheng/grasp_server/'
PARENT = PROJECT / 'qualified_initial_state_v1/evidence/remote'
ENGINE = PROJECT / 'qualified_closure_dynamics_run_v4/evidence/remote/engine'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def archive_files():
    delivery = read(ROOT / 'evidence/DELIVERY.json')
    lookup, matches = {}, 0
    for row in delivery['files']:
        target = REMOTE / row['name']
        assert target.resolve().is_relative_to(REMOTE.resolve())
        assert target.stat().st_size == row['size']
        assert sha(target) == row['sha256'], row['name']
        lookup[SERVER + row['remote']] = target
        local = PROJECT / row['remote']
        if local.is_file():
            assert sha(local) == row['sha256'], row['remote']
            matches += 1
    for key in ('candidate_status', 'failure_status', 'authorization_status'):
        assert delivery['checks'][key] == 404
    for name in ('candidate_state.npz', 'failure.json'):
        assert not (REMOTE / 'run' / name).exists()
    assert not (ROOT / 'authorization.json').exists()
    return lookup, dict(downloaded=len(delivery['files']), local_source_matches=matches,
                        candidate_saved=False, new_dynamics_authorization=False)


def lineage(lookup):
    manifest = read(REMOTE / 'prepared/manifest.json')
    parent = read(REMOTE / 'inputs/parent_manifest.json')
    assert sha(REMOTE / 'inputs/parent_manifest.json') == sha(PARENT / 'prepared/manifest.json')
    assert sha(REMOTE / 'inputs/parent_audit.json') == sha(PARENT / 'run/audit_result.json')
    for name, digest in parent['identities'].items():
        assert manifest['identities'][name] == digest, name
    for name, path in lookup.items():
        if name in manifest['identities']:
            assert sha(path) == manifest['identities'][name], name
    assert not manifest['execution_authorized'] and manifest['integration_budget'] == 0
    assert not any(manifest['import_counts'].values())
    for name, digest in read(REMOTE / 'run/inventory.json').items():
        assert sha(REMOTE / 'run' / name) == digest
    for local, old in [('v4_claim.json', 'run/claim.json'), ('v4_failure.json', 'run/failure.json'),
                       ('v4_authorization.json', 'authorization.json'), ('initial.json', 'run/initial.json'),
                       ('initial_transform.npz', 'run/initial_transform.npz')]:
        assert sha(REMOTE / 'inputs' / local) == sha(ENGINE / old), local
    assert read(REMOTE / 'inputs/v4_claim.json')['consumed'] == 1
    assert len(parent['identities']) == 8427 and len(manifest['identities']) == 8448
    return dict(prior_identities=8427, identities=8448, old_identities_preserved=True,
                old_claim_failure_and_state_preserved=True)


def results():
    result = read(REMOTE / 'run/result.json')
    audit = read(REMOTE / 'run/audit_result.json')
    assert not result['candidate_created'] and result['rejection'] == 'local_projection_failed'
    right, left = result['solutions']['right'], result['solutions']['left']
    assert right['accepted'] and right['optimizer_success'] and right['status'] == 0
    assert not left['accepted'] and not left['optimizer_success'] and left['status'] == 8
    assert left['message'] == 'Positive directional derivative for linesearch'
    for row in (right, left):
        assert row['attempts'] == 1 and not row['global_minimum_proven']
    assert result['counts'] == dict(integration=0, scene=0, rendering=0, forbidden_model=0,
                                    forward=0, isolated_model=1, data=2)
    for flag in ('geometry_feasible', 'full_scene_checked', 'attach_recomputed', 'collisions_checked',
                 'dynamics_validated', 'production_ready', 'execution_authorized', 'safety_gate_changed'):
        assert not result[flag], flag
    assert audit['passed'] and audit['rejection_evidence_only'] and not audit['candidate_verified']
    assert not any(audit['counts'].values())
    assert sha(REMOTE / 'run/result.json') == audit['result_sha256']
    for item in (result, audit):
        assert item['imports']['verified_identities'] == 8448
        assert not any(item['imports']['import_counts'].values())
    for name, job in [('construction_claim.json', '6869'), ('audit_claim.json', '6870')]:
        assert read(REMOTE / 'run' / name) == dict(consumed=1, integration_budget=0, job=job)
    return dict(candidate_created=False, attempts_per_side=1, rejection_status=8,
                audit_scope='rejection_evidence_only', independent_geometry_verified=False,
                construction_integration=0, audit_integration=0, production_ready=False)


def sources():
    manifest = read(REMOTE / 'prepared/manifest.json')
    count = 0
    for path in ROOT.glob('*.py'):
        content = path.read_text(encoding='utf-8')
        assert len(content.splitlines()) <= 300, path.name
        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
        remote = SERVER + ROOT.name + '/' + path.name
        if remote in manifest['identities']:
            assert sha(path) == manifest['identities'][remote], path.name
            count += 1
    assert count == 7
    return dict(frozen_python_sources=count, review='serial_self_review', frozen_plan_unchanged=True)


def jobs():
    rows = (REMOTE / 'job_status.txt').read_text().splitlines()
    expected = {'6866': 'FAILED|1:0', '6867': 'COMPLETED|0:0', '6868': 'COMPLETED|0:0',
                '6869': 'COMPLETED|0:0', '6870': 'COMPLETED|0:0'}
    for job, state in expected.items():
        assert any(row.startswith(job + '|' + state + '|') for row in rows), job
    red = (REMOTE / 'tests-6866.log').read_text()
    green = (REMOTE / 'tests-6867.log').read_text()
    assert 'ModuleNotFoundError' in red and 'FAILED (errors=1)' in red
    assert 'Ran 4 tests' in green and '\nOK\n' in green
    assert not (REMOTE / 'queue_status.txt').read_text().strip()
    return dict(states=expected, tests_passed=4, red_scope='missing_solver_import', queue_empty=True)


def main():
    lookup, files = archive_files()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
        files=files, lineage=lineage(lookup), results=results(), sources=sources(), jobs=jobs(),
        model_generations=0, training_runs=0, old_experiments_repeated=False,
        production_gate_changed=False)
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8')):
        assert (ROOT / target).is_file() or target == 'evidence/FINAL_VERIFICATION.json', target
    with (ROOT / 'evidence/FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert read(ROOT / 'evidence/FINAL_VERIFICATION.json') == result
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

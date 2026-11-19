"""本地档案与冻结来源核对；不导入仿真、不运行实验。"""
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
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def files():
    delivery = read(ROOT / 'evidence/DELIVERY.json')
    lookup, matches = {}, 0
    for row in delivery['files']:
        archived = REMOTE / row['name']
        assert sha(archived) == row['sha256'], row['name']
        lookup[SERVER + row['remote']] = archived
        local = PROJECT / row['remote']
        if local.is_file():
            assert sha(local) == row['sha256'], row['remote']
            matches += 1
    assert delivery['checks']['v3_run_status'] == 404
    return lookup, dict(downloaded=len(delivery['files']), local_source_matches=matches)


def evidence(lookup):
    auth = read(REMOTE / 'engine/authorization.json')
    registration, audit = read(REMOTE / 'registration.json'), read(REMOTE / 'failure_audit.json')
    prepared = PROJECT / 'qualified_closure_dynamics_v3/evidence/remote/v3/prepared/manifest.json'
    assert auth['preparation_sha256'] == sha(prepared)
    assert auth['identities'] == read(prepared)['identities']
    assert auth['execution_authorized'] and auth['budget'] == registration['budget']
    assert sha(REMOTE / 'engine/authorization.json') == registration['authorization_sha256']
    for group in (registration['sources'], audit['identities']):
        for name, digest in group.items():
            assert sha(lookup[name]) == digest, name
    assert audit['passed'] and audit['scope'] == 'preclaim_import_failure_evidence_only'
    assert not audit['dynamics_validated'] and not audit['production_ready']
    assert audit['run_absent'] and audit['new_claim_consumed'] == 0
    assert audit['setup_steps'] == audit['task_steps'] == audit['audit_integration_steps'] == 0
    assert not audit['counters_persisted'] and not audit['simulation_imported']
    assert audit['dependency']['installed_record_matches']
    assert not audit['dependency']['rejected_binary_previously_bound']
    assert sha(REMOTE / 'dependency/open3d_init.py') == audit['dependency']['selector_sha256']
    attempt = read(REMOTE / 'audit_attempt.json')
    assert attempt['consumed'] == 1 and attempt['job'] == '6852'
    assert sha(ROOT / 'failure_audit.py') == attempt['source_sha256']
    assert sha(ROOT / 'failure_audit.sbatch') == attempt['launcher_sha256']
    prior = PROJECT / 'qualified_closure_dynamics_run_v1/evidence/remote/engine/run/claim.json'
    assert sha(prior) == sha(REMOTE / 'history/v1_claim.json')
    assert read(prior)['consumed'] == 1
    sources = list((PROJECT / 'qualified_closure_dynamics_v3').glob('*.py'))
    for source in sources:
        assert sha(source) == auth['identities'][SERVER + source.relative_to(PROJECT).as_posix()]
    return dict(authorized_identities=len(auth['identities']), frozen_v3_python_sources=len(sources),
        old_v1_claim_preserved=True, new_claim_consumed=0, audit_budget_consumed=1,
        setup_steps=0, task_steps=0, saved_step_counters=False,
        step_count_basis=audit['integration_count_basis'], failure_evidence_audit_passed=True,
        dynamics_validated=False)


def jobs():
    rows = (REMOTE / 'job_status.txt').read_text().splitlines()
    expected = {'6850': 'COMPLETED|0:0', '6851': 'FAILED|1:0', '6852': 'COMPLETED|0:0'}
    for job, state in expected.items():
        assert any(row.startswith(job + '|' + state + '|') for row in rows)
    assert 'gres/gpu=1' in next(row for row in rows if row.startswith('6851|'))
    assert 'gres/gpu' not in next(row for row in rows if row.startswith('6848|'))
    assert 'open3d/cuda/pybind' in (REMOTE / 'execute-6851.log').read_text()
    return expected


def local_checks():
    for source in ROOT.glob('*.py'):
        tree = ast.parse(source.read_text(encoding='utf-8'))
        assert len(source.read_text(encoding='utf-8').splitlines()) <= 300
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
    report = ROOT / 'REPORT.md'
    links = re.findall(r'\]\(([^)]+)\)', report.read_text(encoding='utf-8'))
    for target in links:
        if not target.startswith(('http:', 'https:')):
            assert (ROOT / target).is_file() or target == 'evidence/FINAL_VERIFICATION.json', target
    return dict(syntax_checked=True, report_links=len(links), review='serial_self_review')


def main():
    lookup, counts = files()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
        files=counts, evidence=evidence(lookup), jobs=jobs(), local_checks=local_checks(),
        model_calls=0, training_runs=0, retry_performed=False, production_gate_changed=False)
    with (ROOT / 'evidence/FINAL_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert read(ROOT / 'evidence/FINAL_VERIFICATION.json') == result
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

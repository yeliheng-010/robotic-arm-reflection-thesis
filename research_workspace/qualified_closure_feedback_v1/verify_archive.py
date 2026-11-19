"""本地独立核验预算、请求差异和哈希；不调用模型或仿真。"""
import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
REMOTE = EVIDENCE / 'remote'
RUN = REMOTE / 'run'
OUTPUT = EVIDENCE / 'FINAL_VERIFICATION.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    delivery = read(EVIDENCE / 'DELIVERY.json')['files']
    seen, sources = set(), 0
    for row in delivery:
        assert row['path'] not in seen
        seen.add(row['path'])
        path = (REMOTE / row['path']).resolve()
        assert path.is_relative_to(REMOTE.resolve())
        assert sha(path) == row['sha256'], row['path']
        if len(Path(row['path']).parts) == 1 and path.suffix in ('.py', '.md', '.sh', '.sbatch'):
            assert sha(ROOT / row['path']) == row['sha256'], row['path']
            sources += 1
    inventory = read(RUN / 'delivery_inventory.json')
    for name, digest in inventory['identities'].items():
        assert sha(REMOTE / name) == digest, name
    claim = ROOT.parent / 'qualified_execution_v1/evidence/remote/run/attempt_claim.json'
    assert read(claim)['consumed'] == 1 and sha(claim) == inventory['original_claim_sha256']
    return dict(downloaded=len(seen), byte_identical_sources=sources,
                inventory_files=len(inventory['identities']), old_claim_unchanged=True)


def requests_and_actions():
    folders = [RUN / f'decision_{i}' for i in (1, 2)]
    requests = [read(p / 'request.json') for p in folders]
    bodies = [json.loads(r['messages'][1]['content']) for r in requests]
    responses = [read(p / 'response.json') for p in folders]
    actions = [json.loads(r['text'])['action'] for r in responses]
    assert actions[0] == actions[1]
    assert [r['prompt_tokens'] for r in responses] == [10552, 10606]
    assert all(r['finish_reason'] == 'stop' and r['completion_tokens'] == 44 for r in responses)
    assert requests[0]['image'] == requests[1]['image']
    assert requests[0]['messages'][0] == requests[1]['messages'][0]
    assert bodies[0]['observation'] == bodies[1]['observation']
    assert bodies[0]['actions'] == bodies[1]['actions']
    assert bodies[1]['history'] == bodies[0]['history'] + [dict(action=actions[0],
                                                          feedback=dict(status='rejected', stage='grasp_endpoint'))]
    assert [b['budget']['decisions'] for b in bodies] == [2, 1]
    for index, folder in enumerate(folders, 1):
        claim = read(folder / 'model_claim.json')
        assert claim == dict(ordinal=index, consumed=1, request_sha256=sha(folder / 'request.json'))
        assert read(folder / 'validated.json') == dict(valid=True, action=actions[index - 1])
        assert (folder / 'generation_started.json').exists()
    image = ROOT.parent / 'qualified_task_v1/evidence/images/audit/978505/qualified.png'
    assert sha(image) == read(RUN / 'manifest.json')['identities'][requests[0]['image']]
    return dict(generations=2, distinct_actions=1, feedback_added=True, image_sha256=sha(image))


def outcomes():
    result = read(RUN / 'result.json')
    assert result['rows'] == [dict(ordinal=1, status='rejected', stage='grasp_endpoint'),
                             dict(ordinal=2, status='repeated_rejected_action', stage=None)]
    assert result['model_reservations'] == result['generations_started'] == result['responses_saved'] == 2
    assert result['ready_ordinal'] is None and result['physical_attempts'] == 0
    plan = read(RUN / 'decision_1/private_plan.json')
    assert len(plan['plan']['endpoints']['grasps']) == 8
    assert all(not row['ok'] and row['reason'] == 'collision' for row in plan['plan']['endpoints']['grasps'])
    assert plan == read(RUN / 'audit/decision_1/private_plan.json')
    assert plan['state_check']['passed'] and plan['state_check']['fields'] == 5623
    assert read(RUN / 'audit_result.json')['passed']
    assert not (RUN / 'decision_2/private_plan.json').exists()
    assert not (RUN / 'execution_manifest.json').exists() and not (RUN / 'physical').exists()
    return dict(grasp_endpoints_passed=0, grasp_endpoints_total=8,
                repeated_action_planned=False, new_closure_gate_reached=False,
                physical_registered=False, physical_attempts=0, training_runs=0)


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), files=files(),
                  model=requests_and_actions(), outcomes=outcomes(), verifier_sha256=sha(Path(__file__)))
    log = (REMOTE / 'prepare-6804.log').read_text(encoding='utf-8')
    assert 'Ran 16 tests' in log and '\nOK\n' in log
    result['server_tests_passed'] = 16
    for path in ROOT.glob('*.py'):
        content = path.read_text(encoding='utf-8')
        assert len(content.splitlines()) <= 300
        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path, node.name)
    targets = [(ROOT / value).resolve() for value in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',
                                                (ROOT / 'REPORT.md').read_text(encoding='utf-8'))]
    for target in targets:
        assert target.is_file() or target == OUTPUT.resolve(), target
    result.update(report_links_checked=len(targets), pending_current_scope=[])
    if '--write' in sys.argv:
        with OUTPUT.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    assert OUTPUT.is_file() and all(p.is_file() for p in targets)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()

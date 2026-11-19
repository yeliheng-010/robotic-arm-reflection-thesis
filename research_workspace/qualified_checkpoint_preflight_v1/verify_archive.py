"""本地只读复核来源、动作、审计与预算，不运行模型或仿真。"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
EVIDENCE, REMOTE = ROOT / 'evidence', ROOT / 'evidence/remote'
RUN = REMOTE / 'run'
OUTPUT = EVIDENCE / 'FINAL_VERIFICATION.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    records = read(EVIDENCE / 'DELIVERY.json')['files']
    seen, sources = set(), 0
    for row in records:
        path = (REMOTE / row['path']).resolve()
        assert path.is_relative_to(REMOTE.resolve())
        assert row['path'] not in seen and row['sha256'] == sha(path)
        seen.add(row['path'])
        if len(Path(row['path']).parts) == 1 and path.suffix in ('.py', '.md', '.sbatch', '.sh'):
            assert row['sha256'] == sha(ROOT / row['path'])
            sources += 1
    inventory = read(RUN / 'delivery_inventory.json')
    for name, expected in inventory['identities'].items():
        assert expected == sha(REMOTE / name), name
    old = ROOT.parent / 'qualified_execution_v1/evidence/remote/run/attempt_claim.json'
    assert read(old)['consumed'] == 1 and inventory['original_claim_sha256'] == sha(old)
    return dict(downloaded=len(seen), byte_identical_sources=sources,
                frozen_identities=inventory['frozen_identities'], old_claim_unchanged=True)


def input_and_budget():
    source = ROOT.parent / 'qualified_prompt_checkpoint_v2/evidence/remote/run'
    inputs = read(RUN / 'input.json')
    result = read(source / 'result.json')
    action = json.loads(read(source / 'response.json')['text'])['action']
    assert inputs['action'] == action == result['action']
    assert read(source / 'audit_result.json')['passed']
    body = json.loads(read(source / 'request.json')['messages'][1]['content'])
    assert inputs['history'] == body['history']
    assert inputs['response_sha256'] == sha(source / 'response.json')
    assert inputs['source_request_sha256'] == sha(source / 'request.json')
    manifest = read(RUN / 'manifest.json')
    assert manifest['max_preflight_sessions'] == manifest['max_audit_replays'] == 1
    assert manifest['max_model_calls'] == manifest['max_physical_attempts'] == manifest['max_training_runs'] == 0
    for name in ('preflight_claim.json', 'audit_claim.json'):
        assert read(RUN / name) == dict(consumed=1, input_sha256=sha(RUN / 'input.json'))
    assert not manifest['physical_registered']
    return action


def results():
    summary, audit = read(RUN / 'result.json'), read(RUN / 'audit_result.json')
    assert summary['model_calls'] == summary['physical_attempts'] == summary['training_runs'] == 0
    assert summary['preflight_sessions'] == 1 and summary['ready_for_physical_execution'] is False
    assert audit['passed'] and audit['independent_process']
    assert audit['result'] == read(RUN / 'preflight/result.json')
    assert audit['result'] == {key: summary[key] for key in ('status', 'stage')}
    for name in audit['compared']:
        assert read(RUN / 'preflight' / name) == read(RUN / 'audit' / name), name
    for path, expected in audit['frozen_primary_outputs'].items():
        name = Path(path).relative_to('/home/yeliheng/grasp_server/qualified_checkpoint_preflight_v1/run')
        assert expected == sha(RUN / name)
    guard = read(RUN / 'preflight/zero_motion_guard.json')
    assert guard['blocked_task_integration_requests'] == guard['blocked_gripper_close_requests'] == 0
    result = dict(status=summary['status'], stage=summary['stage'], static_sessions=1,
                  independent_replays=1, model_calls=0, physical=0, training=0, guard=guard,
                  reached_artifacts=audit['compared'])
    plan_path = RUN / 'preflight/private_plan.json'
    if plan_path.exists():
        plan = read(plan_path)
        assert plan['state_check']['passed']
        endpoints = plan['plan']['endpoints']
        grasps = endpoints['grasps']
        result.update(grasp_endpoints_total=len(grasps), grasp_endpoints_passed=sum(row['ok'] for row in grasps),
                      placement_endpoints_total=len(endpoints['goals']), placement_endpoints_passed=endpoints['passing'],
                      strict_paths_passed=plan['strict']['passed'], isolation_fields=plan['state_check']['fields'])
    return result


def closure_summary():
    value = read(RUN / 'preflight/closure.json')
    valid = [row for row in value['envelope'] if row['valid']]
    collision = [row for row in valid if row['contacts']]
    contacts = [contact for row in collision for contact in row['contacts']]
    assert value['envelope_valid'] == len(valid) == 283
    assert value['envelope_collisions'] == len(collision) == 5 and not value['passed']
    assert all(row['valid'] and not row['contacts'] for row in value['rows'])
    assert value['integration_steps'] == 0 and value['isolation']['passed']
    assert not (RUN / 'preflight/commands.json').exists()
    assert not (RUN / 'preflight/preflight.json').exists()
    return dict(nominal_valid=len(value['rows']), nominal_collisions=0,
                envelope_total=len(value['envelope']), envelope_valid=len(valid),
                envelope_invalid=len(value['envelope']) - len(valid), collision_configurations=len(collision),
                contact_count=len(contacts), maximum_penetration_mm=max(-row['distance'] * 1000 for row in contacts),
                native_commands_reached=False, initial_observation_rechecked=False)


def main():
    value = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
                 files=files(), action=input_and_budget(), results=results(), closure=closure_summary(),
                 verifier_sha256=sha(Path(__file__)))
    log = (REMOTE / 'prepare-6820.log').read_text(encoding='utf-8')
    assert 'Ran 4 tests' in log and '\nOK\n' in log
    for path in ROOT.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= 300
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path, node.name)
    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8'))
    assert all((ROOT / link).is_file() or (ROOT / link).resolve() == OUTPUT for link in links)
    value.update(server_tests_passed=4, report_links_checked=len(links), pending_current_scope=[])
    if '--write' in sys.argv:
        with OUTPUT.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    assert OUTPUT.is_file() and all((ROOT / link).is_file() for link in links)
    print(json.dumps(value, ensure_ascii=True))


if __name__ == '__main__':
    main()

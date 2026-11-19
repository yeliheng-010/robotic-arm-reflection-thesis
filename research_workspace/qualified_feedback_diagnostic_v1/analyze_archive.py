"""只读分析旧归档，生成未启用草案；不导入模型、仿真或实验入口。"""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
ARCHIVE = PROJECT / 'qualified_closure_feedback_v1/evidence'
RUN = ARCHIVE / 'remote/run'
REMOTE_ROOT = '/home/yeliheng/grasp_server/'
CONSUMED = {}
STALE_TEXT = '请定位待抓物体和目标容器。'
CHECKPOINT = ('输出前逐项比较拟选动作与history中所有已拒绝动作的完整参数。'
              '不要重复任何已拒绝动作；根据相同观测自主选择另一个白名单内动作。'
              '如果无法选择，输出STOP且args为空对象。仍只输出原约定的action JSON。')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def consume(path):
    CONSUMED[path.relative_to(PROJECT).as_posix()] = digest(path)
    return path.read_text(encoding='utf-8')


def read(path):
    return json.loads(consume(path))


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def archive_integrity():
    delivery = read(ARCHIVE / 'DELIVERY.json')['files']
    for row in delivery:
        path = (ARCHIVE / 'remote' / row['path']).resolve()
        assert path.is_relative_to((ARCHIVE / 'remote').resolve())
        assert row['sha256'] == digest(path), row['path']
        CONSUMED[path.relative_to(PROJECT).as_posix()] = row['sha256']
    result = read(RUN / 'result.json')
    assert result['generations_started'] == result['responses_saved'] == 2
    assert result['ready_ordinal'] is None and result['physical_attempts'] == 0
    assert result['rows'][1]['status'] == 'repeated_rejected_action'
    assert not (RUN / 'decision_2/private_plan.json').exists()
    assert not (RUN / 'execution_manifest.json').exists()
    inventory = read(RUN / 'delivery_inventory.json')
    claim = PROJECT / 'qualified_execution_v1/evidence/remote/run/attempt_claim.json'
    assert read(claim)['consumed'] == 1
    assert inventory['original_claim_sha256'] == digest(claim)
    return dict(downloaded_files_verified=len(delivery), original_claim_unchanged=True)


def compare_requests():
    requests = [read(RUN / f'decision_{i}/request.json') for i in (1, 2)]
    bodies = [json.loads(r['messages'][1]['content']) for r in requests]
    responses = [read(RUN / f'decision_{i}/response.json') for i in (1, 2)]
    actions = [json.loads(r['text'])['action'] for r in responses]
    assert responses[0]['generated_ids'] == responses[1]['generated_ids']
    assert actions[0] == actions[1]
    for i, action in enumerate(actions, 1):
        assert read(RUN / f'decision_{i}/validated.json') == dict(valid=True, action=action)
    expected = deepcopy(bodies[0])
    expected['history'].append(dict(action=actions[0], feedback=dict(status='rejected', stage='grasp_endpoint')))
    expected['budget'] = dict(decisions=1, planning=1, observations=0)
    assert bodies[1] == expected
    assert requests[0]['messages'][0] == requests[1]['messages'][0]
    assert requests[0]['image'] == requests[1]['image']
    image = PROJECT / 'qualified_task_v1/evidence/images/audit/978505/qualified.png'
    manifest = read(RUN / 'manifest.json')['identities']
    assert manifest[requests[0]['image']] == digest(image)
    CONSUMED[image.relative_to(PROJECT).as_posix()] = digest(image)
    stats = dict(input_tokens=[r['prompt_tokens'] for r in responses],
                 output_tokens=[r['completion_tokens'] for r in responses],
                 elapsed_s=[r['elapsed_s'] for r in responses],
                 same_generated_ids=True, same_action=True, raw_feedback_added=True,
                 image_sha256=digest(image), changed_body_fields=['budget', 'history'])
    return requests, bodies, stats


def layout(body, text):
    fields = {key: dict(start_char=text.index('"' + key + '":'),
                       serialized_chars=len(compact(value))) for key, value in body.items()}
    point_keys = ('target_points_world', 'non_target_points_world')
    points = {key: dict(count=len(body['observation'][key]),
                       serialized_chars=len(compact(body['observation'][key]))) for key in point_keys}
    return dict(user_chars=len(text), units='Unicode characters, not tokens', fields=fields,
                points=points, history_entries=len(body['history']))


def action_domain(body):
    allowed = body['actions'][0]['allowed_values']
    assert body['actions'][0]['id'] == 'PROPOSE_GRASP'
    assert body['actions'][1] == dict(id='STOP', allowed_values={})
    candidates = [dict(zip(allowed, values)) for values in itertools.product(*allowed.values())]
    legal = [args for args in candidates if args['tilt_deg'] != 0 or args['azimuth_deg'] == 0]
    rejected = {compact(row['action']) for row in body['history']}
    assert all(row['action']['args'] in legal for row in body['history'])
    assert len(legal) == 738 and len(rejected) == 5
    return dict(schema_legal_grasp_tuples=len(legal), rejected_distinct_tuples=len(rejected),
                stop_allowed=True, untried_safety='unknown; novelty is not safety')


def source_provenance():
    remote = read(ROOT / 'evidence/REMOTE_SOURCE_CHECK.json')
    manifest = read(RUN / 'manifest.json')['identities']
    inventory = read(RUN / 'delivery_inventory.json')
    findings = []
    for row in remote['files']:
        path = PROJECT / row['path']
        source = consume(path)
        assert row['sha256'] == digest(path), row['path']
        ast.parse(source)
        key = REMOTE_ROOT + row['path']
        at_closeout = row['path'] == 'ai_diagnosis_failure_v1/f_generator.py'
        if at_closeout:
            assert inventory['generator_source_sha256'] == row['sha256']
        findings.append(dict(path=row['path'], local_matches_current_remote=True,
                             frozen_at_registration=key in manifest,
                             separately_hashed_at_closeout=at_closeout))
    source_paths = ('model_grasp_intent_v1/contract.py', 'qualified_feedback_v1/policy.py',
                    'qualified_closure_feedback_v1/model.py', 'qualified_closure_feedback_v1/worker.py',
                    'qualified_closure_feedback_v1/policy.py', 'qualified_joint_feedback_v1/policy.py')
    for name in source_paths:
        consume(PROJECT / name)
        assert manifest[REMOTE_ROOT + name] == digest(PROJECT / name), name
    encodings = [read(RUN / f'decision_{i}/encoding.json') for i in (1, 2)]
    assert all(set(row['encoding']) == {'pixel_values_shape', 'image_grid_thw', 'input_tokens'}
               for row in encodings)
    return dict(current_remote_check_utc=remote['checked_at_utc'], sources=findings,
                full_input_tensor_archived=False, processor_template_hash_archived=False,
                historical_tensor_delivery_proven=False)


def draft_requests(original, body):
    checkpoint_body = deepcopy(body)
    checkpoint_body['decision_checkpoint'] = dict(latest_public_rejection=deepcopy(body['history'][-1]),
                                                  instruction=CHECKPOINT)
    cleaned_body = deepcopy(body)
    assert cleaned_body['task_grounding']['task'].count(STALE_TEXT) == 1
    cleaned_body['task_grounding']['task'] = cleaned_body['task_grounding']['task'].replace(STALE_TEXT, '')
    result = {}
    for name, changed in [('B_checkpoint', checkpoint_body), ('C_phase_text', cleaned_body)]:
        request = deepcopy(original)
        request['messages'][1]['content'] = compact(changed)
        result[name] = dict(status='unactivated_not_sent', budget_registered=False,
                            baseline='archived decision_2; exhausted budget cannot be reused', request=request)
    restored = deepcopy(checkpoint_body)
    restored.pop('decision_checkpoint')
    assert restored == body
    restored = deepcopy(cleaned_body)
    restored['task_grounding']['task'] += STALE_TEXT
    assert restored == body
    return result


def save_or_compare(path, value, write):
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    assert read(path) == value, path


def main():
    write = '--write' in sys.argv
    integrity = archive_integrity()
    requests, bodies, comparison = compare_requests()
    provenance = source_provenance()
    analysis = dict(integrity=integrity, comparison=comparison, provenance=provenance,
                    layout=[layout(b, r['messages'][1]['content']) for b, r in zip(bodies, requests)],
                    action_domain=action_domain(bodies[1]),
                    stale_phase_text=STALE_TEXT, neural_cause='not established',
                    new_model_calls=0, new_physical_attempts=0, new_training_runs=0)
    for name, value in draft_requests(requests[1], bodies[1]).items():
        save_or_compare(ROOT / 'drafts' / f'{name}.json', value, write)
    save_or_compare(ROOT / 'evidence/ANALYSIS.json', analysis, write)
    output = ROOT / 'evidence/FINAL_VERIFICATION.json'
    report = consume(ROOT / 'REPORT.md')
    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', report)
    for name in links:
        target = (ROOT / name).resolve()
        assert target.is_file() or target == output, name
    source = consume(Path(__file__))
    assert len(source.splitlines()) <= 300
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef):
            assert node.end_lineno - node.lineno + 1 <= 50, node.name
    verification = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
                        passed=True, mode='local_archive_analysis_only', consumed_sha256=CONSUMED.copy(),
                        report_links_checked=len(links), drafts_single_variable_verified=True,
                        model_calls=0, physics=0, training=0)
    if write:
        with output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(verification, ensure_ascii=False, indent=2) + '\n')
    saved = json.loads(output.read_text(encoding='utf-8'))
    assert saved['consumed_sha256'] == verification['consumed_sha256']
    assert all((ROOT / name).is_file() for name in links)
    print(json.dumps(dict(passed=True, input_files=len(CONSUMED), archive=integrity,
                         input_tokens=comparison['input_tokens'], action_domain=analysis['action_domain'],
                         draft_count=2, new_model_calls=0, physics=0, training=0), ensure_ascii=True))


if __name__ == '__main__':
    main()

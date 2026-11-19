"""从物理轨迹及原始请求独立核验预算、反馈和参数执行。"""
import json
import numpy as np
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters
from stability.collection_worker import verify_pair
from flashnext.client import check_response, parse_correction
from controlled.config import ARMS, MAX_ATTEMPTS, MAX_TOKENS, scenario
from controlled.feedback import project_report, check_action
from controlled.client import messages
from controlled.worker import jsonlines


def audit_records(result, task):
    assert result['scenario'] == scenario(task['seed'], task['level'])
    assert result['test_used'] is False and result['split'] == 'train'
    assert result['scene_jitter_m'] == 0
    assert all(result[k] == task[k] for k in ('source', 'destination', 'fault', 'seed'))
    records = result['records']
    assert 1 <= len(records) == result['attempts'] <= MAX_ATTEMPTS
    assert result['success'] == any(r['accepted'] for r in records)
    assert all(not r['accepted'] or r['physical_success'] for r in records)
    for index, record in enumerate(records):
        assert record['attempt'] == index+1
        sensor = record['domain_randomization']['sensor_frames'][0]
        assert sensor['attempt'] == index+1 and sensor['scene_seed'] == task['seed']
        noisy = task['level'] in ('sensor', 'mixed')
        assert (sensor['noisy_sha256'] != sensor['clean_sha256']) == noisy
        for field in ('initial_qpos', 'initial_body_xyz'):
            np.testing.assert_allclose(records[0]['candidate_trace'][field],
                                       record['candidate_trace'][field], atol=1e-8, rtol=0)
    for before, after in zip(records, records[1:]):
        expected = Parameters().updated(before['parameters']).updated(before.get('reflection', {}).get('changes', {}))
        assert expected == Parameters().updated(after['parameters'])


def audit_feedback(directory, result, *, arm):
    events = jsonlines(directory/'feedback.jsonl')
    calls = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    assert len(calls) == len(events)
    requests = jsonlines(directory/'requests.jsonl')
    assert len(requests) == (len(calls) if arm == 'flash' else 0)
    history = []
    for index, (record, event) in enumerate(zip(calls, events)):
        projected = project_report(record['error'], result['scenario'], attempt=record['attempt'])
        assert projected == event['projected'] and event['history'] == history
        if arm == 'flash':
            audit_request(requests[index], result, record=record, projected=projected, history=history)
        if 'reflection' in record:
            assert record['reflection'] == event['answer']
            history.append({'error': projected, 'reflection': record['reflection']})
        else:
            assert event.get('error')
    return len(calls)


def audit_request(event, result, *, record, projected, history):
    # 当轮报告经过 ErrorReport 序列化，历史仍保持当时的投影；保留逐字核对。
    emitted = ErrorReport(ErrorType(projected['error_type']), projected['message'],
                          projected['evidence'], detector=projected['detector'], timestamp=0).to_dict()
    expected = messages(result['instruction'], emitted, parameters=record['parameters'], history=history)
    assert event['request']['messages'] == expected
    assert event['request']['max_tokens'] == MAX_TOKENS
    if 'reflection' in record:
        count = projected['evidence']['diagnostics'].get('available_candidate_count')
        parameters = Parameters().updated(record['parameters'])
        answer = parse_correction(check_response(event['response']), parameters, candidate_count=count)
        check_action(answer, parameters, candidate_count=count)
        assert answer.to_dict() == event['parsed'] == record['reflection']
    else:
        assert event.get('error')


def audit_case(root, case, task):
    directory = root/'tasks'/f'{case:02d}'
    results = {a: json.loads((directory/a/'result.json').read_text()) for a in ARMS}
    first_sensor = results['retry']['records'][0]['domain_randomization']['sensor_frames'][0]
    calls = {}
    for arm, result in results.items():
        audit_records(result, task)
        verify_pair(result, results['retry'])
        assert first_sensor == result['records'][0]['domain_randomization']['sensor_frames'][0]
        calls[arm] = audit_feedback(directory/arm, result, arm=arm)
    return dict(case=case, passed=True, paired_initial_state=True,
                projected_feedback_verified=True, executed_parameters_verified=True, calls=calls)


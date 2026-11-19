"""从原始四组轨迹复核配对、预算、提示和实际执行。"""
import json
import numpy as np
from reflection.reflector import Parameters
from stability.collection_worker import verify_pair
from stability.loop_freeze import ROOT
from stability.loop_protocol import ARMS, validate_reply
from stability.prompt import parse_response, build_messages


def read(path):
    return json.loads(path.read_text())


def validate_records(result, task):
    assert all(result[k] == v for k, v in task.items())
    assert result['persistent_fault'] and result['scene_jitter_m'] == .012
    assert result['retry_protocol'] == 'restore_same_initial_scene_each_attempt'
    records = result['records']
    assert result['attempts'] == len(records) and 1 <= len(records) <= 3
    assert result['success'] == any(r['accepted'] for r in records)
    assert all(not r['accepted'] or r['physical_success'] for r in records)
    assert result['success'] or len(records) == 3 or 'reflection_error' in records[-1]
    for first, following in zip(records, records[1:]):
        params = Parameters().updated(first['parameters'])
        changes = first.get('reflection', {}).get('changes', {})
        assert params.updated(changes) == Parameters().updated(following['parameters'])
        for field in ('initial_qpos', 'initial_body_xyz'):
            np.testing.assert_allclose(records[0]['candidate_trace'][field],
                following['candidate_trace'][field], atol=1e-8, rtol=0)


def validate_model(directory, result, arm):
    path = directory/'requests.jsonl'
    events = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    calls = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    assert len(events) == len(calls)
    history = []
    for record, event in zip(calls, events):
        prompt = build_messages(result['instruction'], record['error'],
            parameters=record['parameters'], history=history)
        assert event['messages'] == prompt and event['arm'] == arm
        if 'reflection' in record:
            validate_reply(event['response'], arm)
            parsed = parse_response(event['response']['text'], Parameters().updated(record['parameters']))
            assert parsed.to_dict() == record['reflection'] == event['parsed']
            history.append({'error': record['error'], 'reflection': {k: record['reflection'][k]
                            for k in ('cause', 'changes')}})
        else:
            assert event.get('error'), 'Failed reflection must retain error'
    return events


def audit(config, rows):
    assert len(rows) == len(config['tasks'])*len(ARMS)
    server = [json.loads(s) for s in (ROOT/'service_requests.jsonl').read_text().splitlines()]
    clients = []
    for case, task in enumerate(config['tasks']):
        directory = ROOT/'tasks'/f'{case:02d}'
        results = {arm: read(directory/arm/'result.json') for arm in ARMS}
        for arm, result in results.items():
            validate_records(result, task)
            verify_pair(result, results['retry'])
            if arm in ('base', 'adapted'):
                clients.extend(validate_model(directory/arm, result, arm))
    for event in clients:
        matches = [s for s in server if s.get('request') == dict(arm=event['arm'], messages=event['messages'])]
        assert len(matches) == 1
        if 'response' in event:
            assert event['response'] == matches[0]['response']
    assert len(server) == len(clients)
    return dict(passed=True,paired_cases=len(config['tasks']),tasks=len(rows),model_calls=len(clients),
        all_tasks_in_denominator=True,parameter_execution_verified=True,test_used=False)

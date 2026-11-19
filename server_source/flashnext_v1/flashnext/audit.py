"""独立核验配对场景、实际参数执行和原始模型输出。"""
import json
from reflection.reflector import Parameters
from stability.collection_worker import verify_pair
from stability.loop_audit import validate_records
from stability.prompt import build_messages
from flashnext.client import check_response, parse_correction
from flashnext.worker import ROOT, ARMS


def read(path):
    return json.loads(path.read_text())


def audit_model(directory, result):
    path = directory/'requests.jsonl'
    events = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    records = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    assert len(records) == len(events)
    history = []
    for record, event in zip(records, events):
        messages = build_messages(result['instruction'], record['error'],
                                  parameters=record['parameters'], history=history)
        assert messages == event['request']['messages']
        assert event['request']['max_tokens'] == 1024
        if 'reflection' not in record:
            assert event.get('error')
            continue
        text = check_response(event['response'])
        count = record['diagnostics'].get('available_candidate_count')
        answer = parse_correction(text, Parameters().updated(record['parameters']),
                                  candidate_count=count)
        assert answer.to_dict() == event['parsed'] == record['reflection']
        history.append({'error': record['error'], 'reflection': {
            k: record['reflection'][k] for k in ('cause', 'changes')}})
    return len(events)


def audit_case(case, task):
    directory = ROOT/'tasks'/f'{case:02d}'
    results = {arm: read(directory/arm/'result.json') for arm in ARMS}
    for result in results.values():
        validate_records(result, task)
        verify_pair(result, results['retry'])
    calls = audit_model(directory/'flash', results['flash'])
    return dict(case=case, passed=True, model_calls=calls,
                parameter_execution_verified=True, scene_pairing_verified=True)


def summarize(rows):
    return {arm: dict(tasks=len(selected), successes=sum(r['success'] for r in selected),
                     attempts=sum(r['attempts'] for r in selected),
                     invalid=sum(r['invalid'] for r in selected),
                     calls=sum(r['calls'] for r in selected))
            for arm in ARMS if (selected := [r for r in rows if r['arm'] == arm])}


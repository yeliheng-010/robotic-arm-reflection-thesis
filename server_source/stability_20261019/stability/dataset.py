"""从真实请求与反事实重试中导出紧邻成功的纯LLM修正。"""
import hashlib
import json
from reflection.reflector import Parameters
from training.refine.prompt import parse_response
from stability.prompt import project_error, FORMAT

PERSISTENT_FAULTS = ('calibration', 'collision', 'placement')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def examples(result, retry, events, *, task_id, split):
    if result.get('fault') not in PERSISTENT_FAULTS or not result.get('persistent_fault'):
        return []
    if retry.get('success') or any(r['accepted'] for r in retry['records']):
        return []
    output, event_index = [], 0
    records = result['records']
    for index, record in enumerate(records):
        if 'reflection' not in record and 'reflection_error' not in record:
            continue
        event = events[event_index]
        event_index += 1
        if 'reflection' not in record or index+1 == len(records):
            continue
        following, answer = records[index+1], record['reflection']
        if answer['source'] != 'llm' or not (following['accepted'] and following['physical_success']):
            continue
        available = len(following['candidate_trace']['returned'])
        if following['parameters']['candidate_index'] >= available:
            continue
        params = Parameters().updated(record['parameters'])
        assert Parameters().updated(following['parameters']) == params.updated(answer['changes'])
        assert parse_response(event['response']['text'], params).to_dict() == answer == event['parsed']
        user = json.loads(event['messages'][1]['content'])
        assert digest(user['parameters']) == digest(record['parameters'])
        expected_error = project_error(record['error'])
        assert digest(user['error']) == digest(expected_error)
        messages = event['messages'] + [{'role': 'assistant', 'content': event['response']['text']}]
        output.append({'messages': messages, 'metadata': {'task_id': task_id, 'split': split,
            'fault': result['fault'], 'source': result['source'], 'destination': result['destination'],
            'seed': result['seed'], 'attempt': record['attempt'], 'verified_attempt': following['attempt'],
            'teacher_source': 'llm', 'model': event['response']['model'],
            'generation': {k: event['response'][k] for k in
                ('architecture', 'thinking', 'max_new_tokens', 'decoding', 'seed') if k in event['response']},
            'prompt_sha256': digest(event['messages']), 'sample_sha256': digest(messages),
            'result_sha256': digest(result), 'retry_failed': True,
            'format': FORMAT}})
    assert event_index == len(events)
    return output


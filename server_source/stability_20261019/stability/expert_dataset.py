"""真实执行过的程序规则监督；绝不标记为LLM或人工思维链。"""
import copy
import json
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters, RuleReflector
from stability.dataset import digest, PERSISTENT_FAULTS
from stability.prompt import build_messages, FORMAT

SOURCE = 'rule_expert'


def replay(record, history):
    raw = record['error']
    report = ErrorReport(ErrorType(raw['error_type']), raw['message'], raw['evidence'],
                         detector=raw['detector'])
    answer = record['reflection']
    if answer['source'] != 'rule':
        raise ValueError('Expert data cannot relabel LLM or hybrid output')
    expected = RuleReflector().reflect(report, Parameters().updated(record['parameters']), history)
    assert digest(expected.to_dict()) == digest(answer), 'Rule replay differs from executed label'
    return answer


def messages(result, record, *, history, answer):
    error = copy.deepcopy(record['error'])
    count = len(record['candidate_trace']['returned'])
    error['evidence'].setdefault('diagnostics', {})['available_candidate_count'] = count
    previous = [{'error': item['error'], 'reflection': {k: item['reflection'][k]
                 for k in ('cause', 'changes')}} for item in history]
    prompt = build_messages(result['instruction'], error, parameters=record['parameters'], history=previous)
    target = json.dumps({k: answer[k] for k in ('cause', 'changes')}, ensure_ascii=False)
    return prompt+[{'role': 'assistant', 'content': target}]


def examples(result, retry, *, task_id, split):
    if result['fault'] not in PERSISTENT_FAULTS or not result['persistent_fault']:
        return []
    if retry['success'] or any(r['accepted'] for r in retry['records']):
        return []
    rows, history = [], []
    records = result['records']
    for index, record in enumerate(records):
        if 'reflection' not in record:
            continue
        answer = replay(record, history)
        if index+1 < len(records):
            following = records[index+1]
            params = Parameters().updated(record['parameters'])
            matched = params.updated(answer['changes']) == Parameters().updated(following['parameters'])
            assert matched, 'Executed parameters differ from rule label'
            available = len(following['candidate_trace']['returned'])
            if (following['accepted'] and following['physical_success'] and
                    following['parameters']['candidate_index'] < available and params.updated(answer['changes']) != params):
                conversation = messages(result, record, history=history, answer=answer)
                rows.append({'messages': conversation, 'metadata': {
                    'task_id': task_id, 'split': split, 'fault': result['fault'],
                    'source': result['source'], 'destination': result['destination'], 'seed': result['seed'],
                    'attempt': record['attempt'], 'verified_attempt': following['attempt'],
                    'teacher_source': SOURCE, 'label_origin': 'programmatic_rule_reflection', 'model': None,
                    'prompt_origin': 'constructed_from_prior_observations', 'cause_origin': 'original_error_message',
                    'prompt_sha256': digest(conversation[:-1]), 'sample_sha256': digest(conversation),
                    'result_sha256': digest(result), 'retry_sha256': digest(retry), 'retry_failed': True,
                    'format': FORMAT+'-expert-supervision'}})
        history.append({'error': record['error'], 'reflection': answer})
    return rows

"""独立核验真实模型请求、投影历史和实际执行参数。"""
import json
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters
from controlled.audit import audit_records
from controlled.feedback import project_report, check_action
from controlled.worker import jsonlines
from controlled.config import tasks, MAX_TOKENS
from stability.collection_worker import verify_pair
from flashnext.client import parse_correction, check_response
from refinement.client import messages


def emitted(report):
    return ErrorReport(ErrorType(report['error_type']), report['message'], report['evidence'],
                       detector=report['detector'], timestamp=0).to_dict()


def audit_request(event, result, *, record, projected, history, arm):
    expected = messages(result['instruction'], emitted(projected), parameters=record['parameters'],
                        history=history, variant=arm)
    request = event['request']
    assert request['messages'] == expected
    assert request['max_tokens'] == MAX_TOKENS and request['seed'] == 42 and request['temperature'] == 0
    if 'reflection' not in record:
        assert event.get('error')
        return
    count = projected['evidence']['diagnostics'].get('available_candidate_count')
    parameters = Parameters().updated(record['parameters'])
    answer = parse_correction(check_response(event['response']), parameters, candidate_count=count)
    check_action(answer, parameters, candidate_count=count)
    assert answer.to_dict() == event['parsed'] == record['reflection']


def audit_feedback(directory, result, arm):
    feedback, requests = jsonlines(directory/'feedback.jsonl'), jsonlines(directory/'requests.jsonl')
    calls = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    assert len(calls) == len(feedback)
    assert len(requests) == (len(calls) if arm.startswith('flash') else 0)
    history = []
    for index, (record, event) in enumerate(zip(calls, feedback)):
        projected = project_report(record['error'], result['scenario'], attempt=record['attempt'])
        assert projected == event['projected'] and event['history'] == history
        if arm.startswith('flash'):
            audit_request(requests[index], result, record=record, projected=projected, history=history, arm=arm)
        if 'reflection' in record:
            assert record['reflection'] == event['answer']
            history.append({'error': projected, 'reflection': record['reflection']})
        else:
            assert event.get('error')
    return len(calls)


def audit_run(directory, result, item):
    task = tasks()[item['case']]
    audit_records(result, task)
    baseline = directory.parents[2].parent/'controlled_v3/pilot/tasks'/f"{item['case']:02d}"/'retry/result.json'
    original = json.loads(baseline.read_text())
    verify_pair(result, original)
    assert result['records'][0]['domain_randomization'] == original['records'][0]['domain_randomization']
    count = audit_feedback(directory, result, item['arm'])
    return dict(passed=True, calls=count, original_baseline_paired=True, projected_history_verified=True)

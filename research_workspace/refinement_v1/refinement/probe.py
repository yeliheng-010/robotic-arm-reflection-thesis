"""固定历史请求重复调用，量化合法性与动作一致性，不宣称物理成功。"""
import hashlib
import json
import os
import random
import time
from pathlib import Path
from reflection.reflector import Parameters
from controlled.config import MAX_TOKENS
from controlled.feedback import check_action
from stability.collection_status import atomic
from flashnext.client import generate, append, parse_correction, ready
from flashnext.provenance import identity
from refinement.config import ROOT, ORDER_SEED, REPEATS
from refinement.freeze import verify, sha
from refinement.audit import emitted
from refinement.client import messages


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def evaluate(event, item):
    parameters = Parameters().updated(item['parameters'])
    try:
        if 'error' in event:
            raise ValueError(event['error'])
        count = item['report']['evidence']['diagnostics'].get('available_candidate_count')
        answer = parse_correction(event['text'], parameters, candidate_count=count)
        check_action(answer, parameters, candidate_count=count)
        event.update(parsed=answer.to_dict(), action_sha256=digest(answer.changes), legal=True)
        residual = item['report']['evidence'].get('grasp_residual_xy')
        if residual is not None and 'grasp_offset' in answer.changes:
            delta = [answer.changes['grasp_offset'][i]-parameters.grasp_offset[i] for i in range(2)]
            event['grasp_delta_dot_residual'] = sum(a*b for a, b in zip(delta, residual))
    except (ValueError, KeyError, TypeError) as error:
        event.update(legal=False, validation_error=repr(error))


def summarize(events):
    rows = []
    for label in sorted({e['label'] for e in events}):
        for variant in ('flash_old', 'flash_new'):
            group = [e for e in events if e['label'] == label and e['variant'] == variant]
            actions = {e['action_sha256'] for e in group if e.get('legal')}
            rows.append(dict(label=label, variant=variant, calls=len(group),
                             legal=sum(e.get('legal', False) for e in group), unique_legal_actions=len(actions),
                             unique_responses=len({e.get('text', '') for e in group}),
                             direction_dot_products=[e.get('grasp_delta_dot_residual') for e in group]))
    return rows


def run_calls(root, items, result):
    order = [(i, variant, r) for i in range(len(items))
             for variant in ('flash_old', 'flash_new') for r in range(REPEATS)]
    random.Random(ORDER_SEED).shuffle(order)
    atomic(root/'order.json', order)
    for index, variant, repeat in order:
        item = items[index]
        prompt = messages(item['instruction'], emitted(item['report']), parameters=item['parameters'],
                          history=item['history'], variant=variant)
        if variant == 'flash_old':
            assert prompt == item['original_request']['messages']
        event = generate(prompt, max_tokens=MAX_TOKENS)
        event.update(label=item['label'], variant=variant, repeat=repeat, case=item['case'],
                     request_sha256=digest(event['request']))
        evaluate(event, item)
        append(root/'requests.jsonl', event)
        result['events'].append(event)
        result['completed'] = len(result['events'])
        atomic(root/'progress.json', dict(status='running', completed=result['completed'], expected=36))
        if event.get('service_error'):
            raise RuntimeError('Service error; stop diagnostic rather than retry selectively')


def main():
    verify()
    root = ROOT/'diagnostic'
    root.mkdir(exist_ok=False)
    items = json.loads((ROOT/'diagnostic_inputs.json').read_text())
    for item in items:
        assert all(sha(Path(p)) == value for p, value in item['source_hashes'].items())
    result = dict(status='running', expected=36, completed=0, events=[], started_at=time.time(),
                  job=os.environ['SLURM_JOB_ID'], models=ready(), identity=identity(), test_used=False)
    try:
        run_calls(root, items, result)
        verify()
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result.update(ended_at=time.time(), summary=summarize(result['events']))
        atomic(root/'result.json', result)
        atomic(root/'progress.json', {k: result[k] for k in ('status', 'completed', 'expected')})


if __name__ == '__main__':
    main()

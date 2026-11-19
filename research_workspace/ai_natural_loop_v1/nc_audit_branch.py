"""从公开历史重建每个决策，拒绝未来信息与未验证动作执行。"""
from pathlib import Path
from types import SimpleNamespace
from action_check import check
from f_response import validate, finish
from live_budget import apply_action
from nc_common import ROOT, read, sha
from nc_state import Branch
from nc_requests import build
from nc_rule import choose
from nc_audit_frames import view
from nc_audit_attempt import audit


def proposal(event, bundle, *, case, method):
    if method == 'fixed_rule':
        assert event['status'] == 'proposed' and event['action'] == choose(bundle['request'])
        return event['action']
    assert event['status'] != 'policy_error', event
    model = event['model']
    key = f"{case['item']['id']}_{method}_{event['index']}"
    server = ROOT/'service/requests'
    assert read(server/f'{key}_request.json') == dict(condition=case['item']['id'], mode=method,
        ordinal=event['index'], request=bundle['request'], messages=bundle[method+'_messages'])
    saved = read(server/f'{key}_response.json')
    assert {k: v for k, v in model.items() if k != 'validation'} == saved
    response = model['response']
    assert response['identity']['adapter_enabled'] is False
    assert response['finish_reason'] == finish(response['generated_ids'], response['eos_ids'])
    checked = validate(response, bundle['request'], mode=method)
    assert checked == model['validation']
    if not checked['valid']:
        assert event['status'] == 'invalid_output' and 'action' not in event
        return None
    assert event['status'] == 'proposed' and event['action'] == checked['parsed']['action']
    return event['action']


def replay(case, result, *, first, first_view):
    branch = Branch(case['item'], first)
    steps, refs = result['ledger']['steps'], result['views']
    assert steps[0] == first and result['ledger']['item'] == case['item']
    summaries = [view(ref, case) for ref in refs]
    assert summaries[0]['paths'] == first_view['paths']
    assert summaries[0]['public'] == first_view['public'] and summaries[0]['private'] == first_view['private']
    sessions = [audit(case, step) for step in steps]
    cursor, stopped = 0, False
    for event in result['decisions']:
        assert not stopped
        branch.decide()
        assert event['index'] == branch.decisions and event['after_attempt'] == len(branch.ledger['steps'])
        record, recorder, _ = sessions[len(branch.ledger['steps'])-1]
        summary = summaries[cursor]
        assert summary['remaining'] == branch.remaining
        bundle = build(branch, SimpleNamespace(record=record, recorder=recorder),
                       SimpleNamespace(sampler=SimpleNamespace(rows=summary['public'])))
        assert sha(event['input_path']) == event['input_sha256'] and read(event['input_path']) == bundle
        assert read(Path(event['input_path']).with_name(f"event_{event['index']}.json")) == event
        action = proposal(event, bundle, case=case, method=result['method'])
        if action is None or action['id'] == 'STOP':
            stopped = True
            continue
        check(action, bundle['request'])
        branch.remember(action)
        cursor = advance(branch, action, steps=steps, summaries=summaries, cursor=cursor)
    assert branch.terminal or stopped
    assert cursor+1 == len(summaries) and branch.ledger == result['ledger']
    assert result['extra_observations'] == branch.extra and result['new_attempts'] == len(steps)-1
    assert result['model_calls'] == (0 if result['method']=='fixed_rule' else branch.decisions)
    assert result['success'] == steps[-1]['success']
    return dict(success=result['success'], natural_failure_steps=sum(not s['success'] for s in steps),
                executed_recoveries=sum(s['success'] for s in steps[1:]), extra=branch.extra)


def advance(branch, action, *, steps, summaries, cursor):
    current, following = summaries[cursor:cursor+2]
    if action['id'] == 'OBSERVE':
        branch.observe()
        assert following['paths'][:-1] == current['paths']
        assert following['public'][:-1] == current['public']
        assert following['public'][-1]['attempt'] == len(branch.ledger['steps'])
    else:
        expected = apply_action(branch.ledger['steps'][-1]['state'], action)
        step = steps[len(branch.ledger['steps'])]
        assert step['state'] == expected
        branch.append(step)
        assert len(following['paths']) == 1 and following['public'][0]['attempt'] == step['index']
    assert following['remaining'] == branch.remaining
    return cursor+1

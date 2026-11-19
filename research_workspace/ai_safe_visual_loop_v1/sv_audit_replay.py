from pathlib import Path
from types import SimpleNamespace
from nc_state import Branch
from nc_audit_frames import view
from nc_audit_branch import advance
from sv_common import read, sha
from sv_requests import build
from sv_actions import check
from sv_audit_proposal import proposal
from sv_audit_attempt import inspect


def bundle_for(branch, step, summary, evidence):
    session = SimpleNamespace(record=evidence['record'], recorder=evidence['recorder'],
        folder=Path(step['session_path']), step=step)
    observed = SimpleNamespace(paths=summary['paths'],
        sampler=SimpleNamespace(rows=summary['public'], private=summary['private']))
    return build(branch, session, observed)


def replay(case, result, *, first, first_view, cache):
    branch = Branch(case['item'], first)
    steps, refs = result['ledger']['steps'], result['views']
    assert steps[0] == first and result['ledger']['item'] == case['item']
    summaries = [view(ref, case) for ref in refs]
    for key in ('paths', 'public', 'private'):
        assert summaries[0][key] == first_view[key]
    for step in steps:
        if step['session_path'] not in cache:
            cache[step['session_path']] = inspect(case, step)
    cursor, stopped = 0, False
    for event in result['decisions']:
        assert not stopped
        branch.decide()
        assert event['index'] == branch.decisions and event['after_attempt'] == len(branch.ledger['steps'])
        step, summary = steps[len(branch.ledger['steps'])-1], summaries[cursor]
        assert summary['remaining'] == branch.remaining
        bundle = bundle_for(branch, step, summary, cache[step['session_path']])
        assert sha(event['input_path']) == event['input_sha256'] and read(event['input_path']) == bundle
        assert read(Path(event['input_path']).with_name(f"event_{event['index']}.json")) == event
        action = proposal(event, bundle, case=case, method=result['method'])
        if action is None or action['id'] == 'STOP':
            stopped = True
        else:
            check(action, bundle['request'])
            branch.remember(action)
            cursor = advance(branch, action, steps=steps, summaries=summaries, cursor=cursor)
    assert branch.terminal or stopped
    assert cursor+1 == len(summaries) and branch.ledger == result['ledger']
    assert result['extra_observations'] == branch.extra and result['new_attempts'] == len(steps)-1
    assert result['model_calls'] == (0 if result['method'] == 'fixed_rule' else branch.decisions)
    assert result['success'] == steps[-1]['success']
    return dict(success=result['success'], extra=branch.extra, steps=len(steps))

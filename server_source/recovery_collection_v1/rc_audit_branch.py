from pathlib import Path
from nc_state import Branch
from nc_audit_frames import view
from sv_strategy_audit import inspect, advance
from sv_strategy_actions import check
from sv_audit_replay import bundle_for
from check_input import public
from collection_common import read, sha, action


def check_bundle(reference, bundle):
    assert sha(reference['input_path']) == reference['input_sha256']
    assert read(reference['input_path']) == bundle
    public(bundle['request'])
    assert all(sha(p) == h for p,h in zip(bundle['visual']['paths'], bundle['visual']['sha256']))


def replay(case, result, *, first, first_view, cache):
    branch = Branch(case['item'], first)
    steps = result['ledger']['steps']
    assert steps[0] == first and result['ledger']['item'] == case['item']
    assert first['state'] == case['state'] and first['strategy'] == 'original'
    summaries = [view(ref, case) for ref in result['views']]
    assert summaries[0] == first_view
    for step in steps:
        if step['session_path'] not in cache:
            cache[step['session_path']] = inspect(case, step)
    cursor = 0
    for event in result['decisions']:
        branch.decide()
        assert event['index'] == branch.decisions and event['after_attempt'] == len(branch.ledger['steps'])
        step = steps[len(branch.ledger['steps'])-1]
        bundle = bundle_for(branch, step, summaries[cursor], cache[step['session_path']])
        check_bundle(event, bundle)
        path = Path(event['input_path']).with_name(f'event_{branch.decisions}.json')
        assert read(path) == event and event['status'] == 'preregistered_exploration'
        proposed = action(result['method'], branch.decisions-1)
        assert proposed == event['action']
        check(proposed, bundle['request'])
        branch.remember(proposed)
        cursor = advance(branch, proposed, steps=steps, summaries=summaries, cursor=cursor)
    assert branch.terminal and branch.ledger == result['ledger']
    assert cursor+1 == len(summaries) and result['new_attempts'] == len(steps)-1
    assert result['model_calls'] == result['extra_observations'] == 0
    assert result['success'] == steps[-1]['success']
    if result['success']:
        bundle = bundle_for(branch, steps[-1], summaries[-1], cache[steps[-1]['session_path']])
        check_bundle(result['success_input'], bundle)
    else:
        assert result['success_input'] is None
    return dict(success=result['success'], new_attempts=result['new_attempts'], model_calls=0, extra_observations=0)

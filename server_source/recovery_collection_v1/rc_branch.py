"""动作顺序预登记；不查询执行错误原因来选择动作。"""
from contextlib import ExitStack
from nc_state import Branch
from nc_observation import View
from nc_branch import persist
from sv_strategy_branch import next_attempt
from sv_strategy_requests import build
from sv_strategy_actions import check
from check_input import public
from collection_common import save, sha, action


def input_bundle(branch, current, view, folder):
    bundle = build(branch, current, view)
    public(bundle['request'])
    path = folder/f'input_{len(branch.ledger["steps"])}.json'
    save(path, bundle)
    return bundle, dict(input_path=str(path), input_sha256=sha(path))


def run(case, first, *, shared, method, folder):
    branch, current = Branch(case['item'], first.step), first
    view = View(first, folder=folder/'observations/attempt_1', remaining=branch.remaining, shared=shared)
    events, views = [], [persist(view, folder/'views')]
    success_input = None
    with ExitStack() as stack:
        while not branch.terminal:
            bundle, reference = input_bundle(branch, current, view, folder/'decisions')
            proposed = action(method, len(events))
            check(proposed, bundle['request'])
            branch.decide()
            event = dict(reference, index=branch.decisions, after_attempt=len(branch.ledger['steps']),
                action=proposed, status='preregistered_exploration')
            save(folder/'decisions'/f'event_{branch.decisions}.json', event)
            events.append(event)
            branch.remember(proposed)
            current = next_attempt(case, branch, action=proposed, folder=folder, stack=stack)
            view = View(current, folder=folder/f'observations/attempt_{current.index}', remaining=branch.remaining)
            views.append(persist(view, folder/'views'))
        if branch.ledger['steps'][-1]['success']:
            _, success_input = input_bundle(branch, current, view, folder/'success')
    value = dict(method=method, ledger=branch.ledger, decisions=events, views=views,
        success=branch.ledger['steps'][-1]['success'], success_input=success_input,
        new_attempts=len(branch.ledger['steps'])-1, model_calls=0, extra_observations=0)
    save(folder/'result.json', value)
    return value

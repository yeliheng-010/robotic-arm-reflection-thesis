from contextlib import ExitStack
from nc_common import save
from nc_state import Branch
from nc_session import opened
from nc_observation import View
from nc_decide import decide
from nc_branch import persist
from sv_strategy_actions import apply


def next_attempt(case, branch, *, action, folder, stack):
    state, strategy = apply(branch.ledger['steps'][-1], action)
    stack.close()
    index = len(branch.ledger['steps'])+1
    current = stack.enter_context(opened(dict(case, strategy=strategy), state,
        folder=folder/f'attempt_{index}', index=index))
    branch.append(current.step)
    return current


def run(case, first, *, shared, method, folder):
    branch = Branch(case['item'], first.step)
    current, events, views = first, [], []
    view = View(first, folder=folder/'observations/attempt_1', remaining=branch.remaining, shared=shared)
    views.append(persist(view, folder/'views'))
    end = 'success' if branch.terminal else None
    with ExitStack() as stack:
        while not branch.terminal:
            action, event = decide(branch, current, view=view, method=method, folder=folder/'decisions')
            events.append(event)
            save(folder/'decisions'/f'event_{branch.decisions}.json', event)
            if action is None or action['id'] == 'STOP':
                end = event['status'] if action is None else 'policy_stop'
                break
            branch.remember(action)
            if action['id'] == 'OBSERVE':
                branch.observe()
                view.capture()
            else:
                current = next_attempt(case, branch, action=action, folder=folder, stack=stack)
                view = View(current, folder=folder/f'observations/attempt_{current.index}', remaining=branch.remaining)
            views.append(persist(view, folder/'views'))
    success = branch.ledger['steps'][-1]['success']
    end = 'success' if success else end or 'execution_budget_exhausted'
    value = dict(method=method, ledger=branch.ledger, success=success, status=end, decisions=events,
        views=views, extra_observations=branch.extra, model_calls=0 if method == 'fixed_rule' else branch.decisions,
        new_attempts=len(branch.ledger['steps'])-1)
    save(folder/'result.json', value)
    return value

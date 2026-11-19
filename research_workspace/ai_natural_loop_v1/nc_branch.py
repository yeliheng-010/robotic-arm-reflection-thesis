"""共享前缀后的有限闭环；OBSERVE真实执行，新动作严格消费一次尝试。"""
from contextlib import ExitStack
from live_budget import apply_action
from nc_common import save, sha
from nc_state import Branch
from nc_session import opened
from nc_observation import View
from nc_decide import decide


def persist(view, folder):
    path = folder/f"a{view.sampler.attempt}_o{view.sampler.budget.count-1}.json"
    save(path, view.summary())
    return dict(path=str(path), sha256=sha(path))


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
                state = apply_action(branch.ledger['steps'][-1]['state'], action)
                stack.close()
                index = len(branch.ledger['steps'])+1
                current = stack.enter_context(opened(case, state, folder=folder/f'attempt_{index}', index=index))
                branch.append(current.step)
                view = View(current, folder=folder/f'observations/attempt_{index}', remaining=branch.remaining)
            views.append(persist(view, folder/'views'))
    success = branch.ledger['steps'][-1]['success']
    end = 'success' if success else end or 'execution_budget_exhausted'
    value = dict(method=method, ledger=branch.ledger, success=success, status=end, decisions=events,
                 views=views, extra_observations=branch.extra, model_calls=0 if method=='fixed_rule' else branch.decisions,
                 new_attempts=len(branch.ledger['steps'])-1)
    save(folder/'result.json', value)
    return value

"""先保存共同快照，再提议和校验；只把有效动作交给执行器。"""
from action_check import check
from nc_common import save, sha
from nc_requests import build
from nc_rule import choose
from nc_client import generate


def decide(branch, session, *, view, method, folder):
    branch.decide()
    ordinal = branch.decisions
    bundle = build(branch, session, view)
    path = folder/f'decision_{ordinal}.json'
    save(path, bundle)
    event = dict(index=ordinal, after_attempt=len(branch.ledger['steps']),
                 input_path=str(path), input_sha256=sha(path), status='proposed')
    try:
        if method == 'fixed_rule':
            action = choose(bundle['request'])
        else:
            model = generate(bundle, condition=branch.ledger['item']['id'], method=method, ordinal=ordinal)
            event['model'] = model
            if not model['validation']['valid']:
                event.update(status='invalid_output', error=model['validation']['error'])
                return None, event
            action = model['validation']['parsed']['action']
        check(action, bundle['request'])
        event['action'] = action
        return action, event
    except Exception as error:
        event.update(status='policy_error', error=repr(error))
        return None, event

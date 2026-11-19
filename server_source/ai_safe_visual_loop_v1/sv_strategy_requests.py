from sv_requests_v2 import build as original
from prompts import messages
from sv_strategy_actions import STRATEGY_ACTION, TOP


def decorate(bundle, strategy):
    assert strategy in ('original', TOP)
    request = bundle['request']
    request['state']['grasp_strategy'] = strategy
    request['version'] = 'safe-visual-loop-v4'
    if strategy == TOP:
        request['actions'] = [r for r in request['actions'] if r['id'] != 'SET_GRASP_OFFSET']
    elif request['budget']['executions_remaining'] > 0:
        request['actions'].append(dict(id=STRATEGY_ACTION,
            effect='切换为本次含噪点云的水平顶面中心与短轴抓取，清零旧偏移；消耗1执行预算，保留全部安全检查。',
            args_spec={'value':'observed_top'}))
    request['execution_semantics']['grasp_strategy'] = (
        'original uses existing grasp candidates and explicit offsets; observed_top estimates a horizontal top '
        'from current noisy points, targets 30mm below that surface, chooses its short axis, and limits '
        'translation from the original candidate to 50mm. Partial surfaces may bias it; success is not guaranteed. '
        'Switching clears prior grasp_offset; direct offsets are unavailable while observed_top is active.')
    for mode in ('direct','diagnostic'):
        bundle[mode+'_messages'] = messages(request, mode=mode)
    return bundle


def build(branch, session, view):
    return decorate(original(branch, session, view), session.step['strategy'])

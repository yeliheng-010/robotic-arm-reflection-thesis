"""闭环开发评估协议。"""
ARMS = ('retry', 'rule', 'base', 'adapted')
PORT = 18825
MAX_NEW_TOKENS = 256
WORKERS = 2


def plan():
    return [dict(source=s, destination=d, fault=f, seed=40000)
            for s, d in (('RedBlock', 'SortingTray'), ('GreenCylinder', 'RedBin'))
            for f in ('calibration', 'collision', 'placement')]


def validate_call(request):
    if not isinstance(request, dict) or set(request) != {'arm', 'messages'}:
        raise ValueError('Expected arm and messages')
    arm, messages = request['arm'], request['messages']
    if arm not in ('base', 'adapted') or not isinstance(messages, list) or len(messages) != 2:
        raise ValueError('Invalid model arm or message count')
    for message, role in zip(messages, ('system', 'user')):
        if message.get('role') != role or not isinstance(message.get('content'), str) or not message['content']:
            raise ValueError('Invalid prompt role or text')
    return arm, messages


def validate_reply(reply, arm):
    if reply.get('arm') != arm or not isinstance(reply.get('text'), str):
        raise ValueError('Model reply arm or text mismatch')


def summarize(rows):
    result = {}
    for arm in ARMS:
        selected = [r for r in rows if r['arm'] == arm]
        if not selected:
            continue
        calls = sum(r['calls'] for r in selected)
        invalid = sum(r['invalid'] for r in selected)
        result[arm] = dict(tasks=len(selected), successes=sum(r['success'] for r in selected),
            success_rate=sum(r['success'] for r in selected)/len(selected),
            mean_attempts=sum(r['attempts'] for r in selected)/len(selected),
            calls=calls, invalid=invalid, invalid_output_rate=invalid/calls if calls else None,
            service_errors=sum(r['service_errors'] for r in selected))
    return result

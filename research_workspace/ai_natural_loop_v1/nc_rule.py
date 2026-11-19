"""预登记通用基线，只读取同一公开请求；不猜隐藏根因。"""
TIME_SEQUENCE = (1.5, 2.)


def choose(request):
    actions = {row['id'] for row in request['actions']}
    frames = next(row['value'] for row in request['evidence'] if row['field'] == 'rgbd_surface_observations')
    unknown = any(v['status'] == 'insufficient_visible_depth' for v in frames[-1]['observed'].values())
    if unknown and 'OBSERVE' in actions:
        return dict(id='OBSERVE', args={})
    if 'SET_TIME_SCALE' in actions:
        current = request['state']['time_scale']
        value = next((v for v in TIME_SEQUENCE if v > current), None)
        if value is not None:
            return dict(id='SET_TIME_SCALE', args={'value': value})
    return dict(id='RETRY' if 'RETRY' in actions else 'STOP', args={})

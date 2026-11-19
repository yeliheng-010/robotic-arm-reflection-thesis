from visual_requests_v2 import build as original
from prompts import messages


def build(branch, session, view):
    bundle = original(branch, session, view)
    request = bundle['request']
    request['version'] = 'safe-visual-loop-v1'
    request['execution_semantics'].update(
        lift_height='Relative upward transport distance AFTER closing the gripper, not absolute grasp height.',
        grasp_offset='Additive world XYZ displacement of the commanded grasp target, metres.',
        observe='Same paused state and fixed camera pose, newly rendered RGB/depth noise; no camera movement or time advance.')
    for action in request['actions']:
        if action['id'] == 'SET_GRASP_OFFSET':
            action.update(effect='单个世界坐标轴增减最多30mm；累计各轴偏移不超过50mm；消耗1执行预算，保留全部安全检查。',
                args_spec={'delta_m': 'three finite numbers; exactly one nonzero axis; abs <= 0.03 m; resulting offset abs <= 0.05 m'})
    bundle['direct_messages'] = messages(request, mode='direct')
    bundle['diagnostic_messages'] = messages(request, mode='diagnostic')
    return bundle

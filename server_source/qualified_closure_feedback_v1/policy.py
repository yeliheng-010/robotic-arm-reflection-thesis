"""仅公开阶段拒绝，不向模型提供构型或碰撞位置。"""
from copy import deepcopy
from qualified_joint_feedback_v1 import policy as parent
from qualified_feedback_v1.policy import permitted

GEOMETRY_KEYS = parent.GEOMETRY_KEYS
STAGES = parent.STAGES + ('gripper_closure', 'execution_entry', 'initial_observation')


def entry(action, stage):
    if stage not in STAGES:
        raise ValueError('unsupported_feedback_stage')
    return dict(action=deepcopy(action), feedback=dict(status='rejected', stage=stage))


def request(context, history, *, remaining):
    if type(remaining) is not int or not 1 <= remaining <= 2:
        raise ValueError('invalid_budget')
    for row in history:
        if set(row) != {'action', 'feedback'} or set(row['feedback']) != {'status', 'stage'}:
            raise ValueError('private_history_fields')
        if row['feedback']['status'] != 'rejected' or row['feedback']['stage'] not in STAGES:
            raise ValueError('invalid_feedback')
    result = parent.request(context['original'], history, remaining=remaining,
                            geometry=context['geometry'], grounding=context['grounding'])
    result['messages'][0]['content'] += '\ngripper_closure表示闭合阶段预检拒绝，不提供原因或推荐姿态。'
    return result

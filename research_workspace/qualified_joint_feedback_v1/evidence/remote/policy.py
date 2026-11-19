"""公开观测与阶段反馈；不向模型暴露私有安全诊断。"""
from copy import deepcopy
import json
from qualified_feedback_v1.policy import permitted

STAGES = ('grasp_proposal', 'grasp_endpoint', 'place_endpoint', 'path', 'return_home')
GEOMETRY_KEYS = ('centers', 'floor_z', 'rim_z', 'source_center', 'source_half', 'edges')
GUIDANCE = '''
目标是完整抓取、搬运、放置、回程。抓取端点可行不保证放置或整条路径可行。
observed_placement仅由预测掩码与含噪深度估计，单位米，不是完整真值。
运输保持所选抓姿方向；执行器将为该姿态检查已观测放置位置和原合法运动分支。
history仅说明已尝试动作在哪个阶段未通过，不提供原因或正确答案。
请结合相同RGB、物体和邻域点云、目标箱位置，自主选一个不同的抓姿或STOP。
禁止重复被拒绝的动作，禁止更改相机、安全门槛或预算；仍须遵守原标量JSON格式。
'''


def compact(value):
    if isinstance(value, list):
        return [compact(v) for v in value]
    return round(value, 5) if isinstance(value, float) else value


def entry(action, stage):
    if stage not in STAGES:
        raise ValueError('unsupported_feedback_stage')
    return dict(action=deepcopy(action), feedback=dict(status='rejected', stage=stage))


def request(original, history, *, remaining, geometry, grounding):
    result = deepcopy(original)
    body = json.loads(result['messages'][1]['content'])
    body['history'] = deepcopy(history)
    body['budget'] = dict(decisions=remaining, planning=remaining, observations=0)
    body['observed_placement'] = {key: compact(geometry[key]) for key in GEOMETRY_KEYS}
    body['task_grounding'] = deepcopy(grounding)
    result['messages'][0]['content'] += GUIDANCE
    result['messages'][1]['content'] = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
    return result


def outcome(result):
    plan, strict = result['plan'], result['strict']
    if not any(row['ok'] for row in plan['endpoints']['grasps']):
        stage = 'grasp_endpoint'
    elif not plan['endpoints']['passing']:
        stage = 'place_endpoint'
    elif strict['passed']:
        return dict(status='ready', stage='complete_static_preflight')
    elif 'return_home' in strict and strict['return_home']['selected'] is None:
        stage = 'return_home'
    else:
        stage = 'path'
    return dict(status='rejected', stage=stage)

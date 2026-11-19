"""相同证据和权限，明确重置语义及时间倍率范围；不加入工程根因。"""
from live_requests_v2 import build as previous_build
from prompts import messages


def build(ledger, record, *, sampler, telemetry, bridge):
    bundle = previous_build(ledger, record, sampler=sampler, telemetry=telemetry, bridge=bridge)
    request = bundle['request']
    request['execution_semantics'] = dict(
        retry='Each execution resets to the registered initial scene; this observation describes the paused previous attempt.',
        time_scale='Scales the three grasp and three transport durations only; gripper and return-home durations are unchanged.',
        offline='This is a recorded decision snapshot. Proposals in this evaluation are never executed.')
    for action in request['actions']:
        if action['id'] == 'SET_TIME_SCALE':
            action['effect'] = '设定三段抓取和三段搬运的时间倍率为1至3；夹爪/回零不变；扣1执行预算。'
    return dict(request=request, direct_messages=messages(request, mode='direct'),
                diagnostic_messages=messages(request, mode='diagnostic'))

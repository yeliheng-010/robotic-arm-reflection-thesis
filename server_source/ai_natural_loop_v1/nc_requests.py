"""三方法共同输入；能力来自已验证接线，不从理想错误类别构造菜单。"""
import json
from copy import deepcopy
from boundary import build_request
from prompts import messages
from nc_common import MAX_OBSERVATIONS

CAPABILITIES = ('OBSERVE', 'RETRY', 'SET_TIME_SCALE', 'SET_GRASP_OFFSET')


def build(branch, session, view):
    raw = session.record
    fields = ('action', 'motion_segment', 'commanded_tcp_xyz', 'available_candidate_count')
    diagnostic = {k: v for k, v in raw.get('diagnostics', {}).items() if k in fields and v is not None}
    command = json.loads(json.dumps(dict(parameters=raw['parameters'], diagnostics=diagnostic), allow_nan=False))
    request = build_request(branch.ledger, command, supported=CAPABILITIES, observations_remaining=branch.remaining)
    request.update(version='natural-closed-loop-v1', scope='assisted_depth_and_robot_telemetry')
    rows = [dict(field='rgbd_surface_observations', value=deepcopy(view.sampler.rows), source='rendered_noisy_depth'),
            dict(field='robot_telemetry', value=session.recorder.public(), source='simulated_encoders_and_commands'),
            dict(field='action_history', value=deepcopy(branch.history), source='previous_policy_actions')]
    for row in rows:
        request['evidence'].append(dict(row, id=f"e{len(request['evidence'])+1}"))
    request['sensing_status'] = dict(rgb='captured_artifact_not_sent_to_text_model',
                                    depth='attached_surface_summary', telemetry='attached_uniform_summary')
    request['execution_semantics'] = dict(
        retry='New execution resets to the registered initial scene; observations describe the prior paused attempt.',
        time_scale='Three grasp and three transport segments only; gripper and return-home durations unchanged.',
        observation_budget=f'At most {MAX_OBSERVATIONS} extra observations across the entire trajectory, not per attempt.')
    for row in request['actions']:
        if row['id'] == 'SET_TIME_SCALE':
            row['effect'] = '设定三段抓取/三段搬运时间倍率1至3；夹爪和回零不变；扣1执行预算。'
    return dict(request=request, direct_messages=messages(request, mode='direct'),
                diagnostic_messages=messages(request, mode='diagnostic'))

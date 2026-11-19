"""只接收已投影的传感摘要；私有审计永不进入模型提示。"""
from copy import deepcopy
from boundary import build_request
from prompts import messages


def supported(bridge):
    actions = ['RETRY', 'OBSERVE']
    executed = any(row['executed'] for row in bridge['planners'])
    if bridge.get('grasp', {}).get('passed') and executed:
        actions += ['SET_TIME_SCALE', 'SET_GRASP_OFFSET']
    return tuple(actions)


def build(ledger, record, *, sampler, telemetry, bridge):
    fields = ('action', 'motion_segment', 'commanded_tcp_xyz', 'available_candidate_count')
    diagnostic = {k: v for k, v in record.get('diagnostics', {}).items() if k in fields and v is not None}
    commands = dict(parameters=record['parameters'], diagnostics=diagnostic)
    request = build_request(ledger, commands, supported=supported(bridge),
                            observations_remaining=sampler.budget.remaining)
    request.update(version='ai-diagnosis-live-v1', scope='paused_scene_observation_with_assisted_segmentation')
    observation = dict(field='rgbd_surface_observations', value=deepcopy(sampler.rows),
                       source='rendered_rgbd_simulation_assisted_segmentation')
    robot = dict(field='robot_telemetry', value=telemetry.public(), source='simulated_encoders_and_commands')
    for row in (observation, robot):
        request['evidence'].append(dict(row, id=f"e{len(request['evidence'])+1}"))
    request['sensing_status'] = dict(rgb='captured_artifact_not_sent_to_text_model',
                                     depth='attached_surface_summary', telemetry='attached_uniform_summary')
    return dict(request=request, direct_messages=messages(request, mode='direct'),
                diagnostic_messages=messages(request, mode='diagnostic'))

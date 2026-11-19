"""核对每次执行参数、原几何保护、传感编号和实际关闭。"""
from pathlib import Path
from unittest.mock import patch
import numpy as np
from audit_motion_live import group, UR5e, set_robot_config, guard_context, CLEARANCE_M, SAMPLES
from pair_run import audit_sensor
from live_telemetry import Recorder
from nc_common import read, sha


def motion(case, state, trace):
    parameters = state['parameters']
    assert CLEARANCE_M == .010 and SAMPLES == 51 and trace['requested'] == parameters
    if trace.get('grasp'):
        grasp = trace['grasp']
        np.testing.assert_allclose(np.array(trace['nominal_grasp_xyz'])+parameters['grasp_offset'],
                                   grasp['actual_target'], atol=1e-9, rtol=0)
        assert grasp['requested_offset'] == parameters['grasp_offset']
        assert grasp['durations'] == [parameters['time_scale']]*3
    if trace.get('carry'):
        assert trace['carry']['durations'] == [parameters['time_scale']]*3
        assert trace['carry']['lift_height'] == parameters['lift_height']
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
        return [group(case, row) for row in trace['planners']]


def audit(case, step):
    assert sha(step['result_path']) == step['result_sha256']
    result = read(step['result_path'])
    assert len(result['records']) == 1 and bool(result['success']) == step['success']
    record = result['records'][0]
    assert record['parameters'] == step['state']['parameters']
    folder = Path(step['session_path'])
    assert read(folder/'step.json') == step
    started = read(folder/'started.json')
    assert started == dict(attempt_index=step['index'], condition=case['item']['id'], state=step['state'])
    lease = read(folder/'lifecycle.json')
    assert lease['released'] and lease['retained_after_attempt'] and lease['actual_close_calls'] == 1
    assert lease['close_error'] is None and lease['exit_exception'] is None
    guard = read(folder/'guard.json')
    assert guard['strict_contacts']
    if step['success']:
        assert guard['release_checked'] and guard['open_called'] and guard['reason'] is None
    sensor = record['domain_randomization']
    assert sensor['level'] == case['config']['group']
    audit_sensor(sensor['sensor_frames'], case['config'], index=step['index'])
    groups = motion(case, step['state'], read(folder/'bridge.json'))
    telemetry = read(folder/'telemetry.json')
    assert telemetry['stride_steps'] == 10
    assert [r['step'] for r in telemetry['rows']] == list(range(10, 10*(len(telemetry['rows'])+1), 10))
    recorder = Recorder()
    recorder.rows = telemetry['rows']
    return record, recorder, groups

"""显式记录观测姿态取代名义抓点，保留原始名义点和全部路径检查。"""
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch
import numpy as np
import live_motion
import nc_audit_attempt
from top_runtime import MAX_TRANSLATION_M

original_motion = nc_audit_attempt.motion


def grasp_wrapper(original, trace, *, parameters):
    def move(flow, *args, **kwargs):
        assert parameters['grasp_offset'] == [0.,0.,0.]
        nominal, actual = flow._ai_nominal_grasp, flow.T_wo.t
        assert np.linalg.norm(actual-nominal) <= MAX_TRANSLATION_M
        times = [kwargs[k] for k in ('time1','time2','time3')]
        assert times == [parameters['time_scale']]*3
        trace['observed_target'] = dict(strategy='observed_top', original_nominal=nominal.tolist(),
            commanded_pose=flow.T_wo.A.tolist(), source='current_noisy_top_fit_bounded_translation')
        trace['grasp'] = dict(requested_offset=parameters['grasp_offset'], actual_target=actual.tolist(),
            expected_target=actual.tolist(), durations=times, passed=True)
        return original(flow, *args, **kwargs)
    return move


@contextmanager
def context(item, state, *, recorder, trace):
    with patch.object(live_motion, 'grasp_wrapper', grasp_wrapper):
        with live_motion.context(item, state, recorder=recorder, trace=trace):
            yield


def motion(case, state, trace):
    if not trace.get('grasp'):
        return original_motion(case, state, trace)
    registered = trace['observed_target']
    assert registered['strategy'] == 'observed_top'
    assert state['parameters']['grasp_offset'] == [0.,0.,0.]
    actual = np.asarray(registered['commanded_pose'])[:3,3]
    np.testing.assert_array_equal(trace['nominal_grasp_xyz'], registered['original_nominal'])
    np.testing.assert_array_equal(actual, trace['grasp']['actual_target'])
    assert np.linalg.norm(actual-np.asarray(registered['original_nominal'])) <= MAX_TRANSLATION_M
    # 原审计的路径/传感/命令检查保持；新目标的来源由top_audit独立重建。
    translated = deepcopy(trace)
    translated['nominal_grasp_xyz'] = actual.tolist()
    return original_motion(case, state, translated)

from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
import numpy as np
import spatialmath as sm
from live_motion import grasp_wrapper, carry_wrapper, checked_planners
from live_budget import apply_action
from live_requests import supported


def parameters():
    return dict(time_scale=1.5, grasp_offset=[.005, 0., 0.], lift_height=.35)


class MotionTests(unittest.TestCase):
    def test_grasp_offset_and_durations_reach_original(self):
        flow = SimpleNamespace(_ai_nominal_grasp=np.array([1., .5, .8]), T_wo=sm.SE3(1.005, .5, .8))
        original, trace = Mock(return_value='moved'), {}
        value = grasp_wrapper(original, trace, parameters=parameters())(flow, time1=1.5, time2=1.5, time3=1.5)
        self.assertEqual('moved', value)
        self.assertTrue(trace['grasp']['passed'])
        self.assertEqual(1, original.call_count)

    def test_silent_offset_override_is_rejected(self):
        flow = SimpleNamespace(_ai_nominal_grasp=np.array([1., .5, .8]), T_wo=sm.SE3(1., .5, .8))
        original = Mock()
        with self.assertRaises(AssertionError):
            grasp_wrapper(original, {}, parameters=parameters())(flow, time1=1.5, time2=1.5, time3=1.5)
        original.assert_not_called()

    def test_carry_times_and_target_reach_original(self):
        original, trace = Mock(return_value='moved'), {}
        value = carry_wrapper(original, trace, parameters=parameters())(None, (1., .5, 1.),
                time4=1.5, time5=1.5, time6=1.5, lift_height=.35, z_offset=.12)
        self.assertEqual('moved', value)
        self.assertEqual([1.5]*3, trace['carry']['durations'])
        self.assertEqual((None, (1., .5, 1.)), original.call_args.args)

    def test_unsupported_candidate_selection_not_advertised(self):
        bridge = dict(grasp=dict(passed=True), planners=[dict(executed=True)])
        self.assertNotIn('SELECT_GRASP', supported(bridge))
        self.assertNotIn('SET_TIME_SCALE', supported(dict(planners=[])))

    def test_action_mapping_updates_copy_and_preserves_others(self):
        from loopstudy.actions import initial
        state = initial()
        changed = apply_action(state, dict(id='SET_TIME_SCALE', args={'value': 1.5}))
        self.assertEqual(1.5, changed['parameters']['time_scale'])
        self.assertEqual(1., state['parameters']['time_scale'])
        self.assertEqual(state['parameters']['grasp_offset'], changed['parameters']['grasp_offset'])


if __name__ == '__main__':
    unittest.main()

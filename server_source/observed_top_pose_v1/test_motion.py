import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import top_motion


class MotionTests(unittest.TestCase):
    def test_command_keeps_original_nominal_and_is_independently_checked(self):
        parameters = dict(grasp_offset=[0.,0.,0.], time_scale=1.5)
        nominal = np.array([1.,.1,.8])
        flow = SimpleNamespace(_ai_nominal_grasp=nominal, T_wo=sm.SE3.Trans(1.01,.09,.79))
        trace = dict(nominal_grasp_xyz=nominal.tolist())
        wrapped = top_motion.grasp_wrapper(lambda *a,**k:'executed', trace, parameters=parameters)
        self.assertEqual('executed', wrapped(flow, time1=1.5,time2=1.5,time3=1.5))
        self.assertEqual(nominal.tolist(), trace['nominal_grasp_xyz'])
        with patch.object(top_motion, 'original_motion', lambda c,s,t:t):
            checked = top_motion.motion({}, dict(parameters=parameters), trace)
            self.assertEqual(flow.T_wo.t.tolist(), checked['nominal_grasp_xyz'])
            trace['observed_target']['original_nominal'][0] += .01
            with self.assertRaises(AssertionError):
                top_motion.motion({}, dict(parameters=parameters), trace)

    def test_far_targets_and_double_offset_rejected(self):
        flow = SimpleNamespace(_ai_nominal_grasp=np.zeros(3), T_wo=sm.SE3.Trans(.2,0,0))
        parameters = dict(grasp_offset=[0.,0.,0.], time_scale=1.5)
        wrapped = top_motion.grasp_wrapper(lambda *a,**k:None, {}, parameters=parameters)
        with self.assertRaises(AssertionError):
            wrapped(flow, time1=1.5,time2=1.5,time3=1.5)
        parameters['grasp_offset'] = [0.,0.,-.03]
        with self.assertRaises(AssertionError):
            wrapped(flow, time1=1.5,time2=1.5,time3=1.5)

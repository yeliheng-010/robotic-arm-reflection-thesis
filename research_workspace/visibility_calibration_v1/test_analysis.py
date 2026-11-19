import unittest
from visibility_calibration_v1.analysis import accuracy


class AccuracyTests(unittest.TestCase):
    def test_axis_sign_is_unobservable(self):
        truth=dict(center=[0,0,0],axis=[1,0,0])
        result=accuracy(dict(center=[.001,0,0],axis=[-1,0,0]),truth)
        self.assertTrue(result['accurate'])
        self.assertEqual(0.,result['axis_error_deg'])

    def test_good_residual_cannot_override_wrong_center(self):
        truth=dict(center=[0,0,0],axis=[1,0,0])
        result=accuracy(dict(center=[.03,0,0],axis=[1,0,0],p95_m=0.),truth)
        self.assertFalse(result['accurate'])
        self.assertEqual(.03,result['center_error_m'])

    def test_missing_fit_stays_in_failure_denominator(self):
        self.assertFalse(accuracy(None,dict(center=[0,0,0],axis=[1,0,0]))['accurate'])

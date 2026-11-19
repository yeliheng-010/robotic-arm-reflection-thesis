"""先验证新动作边界、竖直坐标系和安全候选选择。"""
import unittest
import numpy as np
import spatialmath as sm
from cm_pose import poses, eligible, select


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.nominal = sm.SE3.Trans(1,.5,.8)*sm.SE3.Ry(.7)

    def test_world_down_axis(self):
        result = poses(self.nominal)
        self.assertEqual(9,len(result))
        for row in result[1:]:
            np.testing.assert_allclose([0,0,-1],row['pose'].R[:,0],atol=1e-12)

    def test_translation_preserved(self):
        for row in poses(self.nominal):
            np.testing.assert_array_equal(self.nominal.t,row['pose'].t)

    def test_first_safe_option(self):
        rows = [dict(id='original',feasible=False),dict(id='down',feasible=True)]
        self.assertEqual(1,select(rows))

    def test_no_safe_means_explicit_fallback(self):
        self.assertIsNone(select([dict(id='original',feasible=False)]))

    def test_only_supported_feedback(self):
        report = dict(error_type='ik_failure',evidence=dict(motion_context=dict(phase='carry_transport')))
        self.assertTrue(eligible(report))
        report['evidence']['motion_context']['phase']='grasp_pose'
        self.assertFalse(eligible(report))

    def test_grasp_collision_is_eligible(self):
        report = dict(error_type='collision',evidence=dict(motion_context=dict(phase='grasp_pose')))
        self.assertTrue(eligible(report))

    def test_success_is_ineligible(self):
        self.assertFalse(eligible(None))


if __name__=='__main__':
    unittest.main()

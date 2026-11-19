"""保持位置，改变姿态优先级，所有补丁必须可恢复。"""
import unittest
import numpy as np
import spatialmath as sm
from drop_recovery import vertical_first, context


class VerticalTests(unittest.TestCase):
    def test_vertical_candidates_precede_unchanged_fallback(self):
        nominal = sm.SE3.Trans(1.2, .8, .8)*sm.SE3.Ry(.7)
        rows = vertical_first(nominal)
        self.assertEqual('original', rows[-1]['id'])
        for row in rows[:-1]:
            np.testing.assert_allclose([0, 0, -1], row['pose'].R[:, 0], atol=1e-12)
            np.testing.assert_array_equal(nominal.t, row['pose'].t)
            self.assertAlmostEqual(0., row['pose'].R[2, 1])
        np.testing.assert_array_equal(nominal.A, rows[-1]['pose'].A)

    def test_context_restores_original_hooks(self):
        import cm_runtime
        import cm_planning
        original = cm_runtime.eligible, cm_planning.poses
        report = dict(error_type='object_dropped', evidence=dict(
            grasp_residual_xy=[0., 0.], motion_context=dict(phase='carry_lift')))
        with self.assertRaisesRegex(RuntimeError, 'sentinel'):
            with context(report, index=3):
                self.assertTrue(cm_runtime.eligible(report))
                self.assertIs(vertical_first, cm_planning.poses)
                raise RuntimeError('sentinel')
        self.assertEqual(original, (cm_runtime.eligible, cm_planning.poses))


if __name__ == '__main__':
    unittest.main()

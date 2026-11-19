"""掉落恢复只在已对准、早期抬升失败时启用。"""
import importlib.util
import unittest


class RecoveryTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('drop_recovery'), '缺少抬升掉落恢复')
        return __import__('drop_recovery')

    def report(self, error='object_dropped', phase='carry_lift'):
        return dict(error_type=error, evidence=dict(grasp_residual_xy=[.0003, .0001],
                    motion_context=dict(phase=phase)))

    def test_centered_lift_drop_is_eligible(self):
        module = self.module()
        self.assertTrue(module.eligible(self.report()))

    def test_success_and_other_phases_are_not_eligible(self):
        module = self.module()
        self.assertFalse(module.eligible(None))
        self.assertFalse(module.eligible(self.report(phase='carry_transport')))
        self.assertFalse(module.eligible(self.report(error='collision')))

    def test_large_missing_and_nonfinite_residuals_do_not_trigger(self):
        module = self.module()
        report = self.report()
        for residual in ([.01, 0.], None, [float('nan'), 0.], [0.], [True, 0.]):
            report['evidence']['grasp_residual_xy'] = residual
            self.assertFalse(module.eligible(report))

    def test_invalid_attempt_does_not_activate(self):
        module = self.module()
        self.assertFalse(module.enabled(index=2, report=self.report()))
        self.assertTrue(module.enabled(index=3, report=self.report()))


if __name__ == '__main__':
    unittest.main()

"""补充检查命令一致性、失败保护和最终入口补丁范围。"""
import unittest
from unittest.mock import patch
import test_wiring
import spatialmath as sm
import op_runtime_v2
import op_runtime
import oc_runtime
import oc_planning
import loopstudy.runtime as loop
from live_motion import plan_values


class ContractTests(unittest.TestCase):
    setUp = test_wiring.WiringTests.setUp
    collect = test_wiring.WiringTests.collect
    def test_collected_commands_equal_execution_commands(self):
        c = self.case
        planned = self.collect()
        c.move(c.robot, c.env, **c.values)
        actual = c.runner.call_args.args
        self.assertEqual(planned['durations'], actual[3])
        before = [('leg', p, t) for p, t in zip(planned['planners'], planned['durations'][1:])]
        after = [('leg', p, t) for p, t in zip(actual[2], actual[3][1:])]
        self.assertEqual(plan_values(before), plan_values(after))

    def test_guard_raises_the_expected_collision_error(self):
        c = self.case
        c.check.return_value = {'feasible': False}
        with self.assertRaisesRegex(Exception, 'Current held-object path rejected'):
            c.move(c.robot, c.env, **c.values)
        c.runner.assert_not_called()

    def test_wrong_grasp_rejected_in_collection_and_execution(self):
        c = self.case
        c.values['T_start'] = c.values['T_start'] * sm.SE3.Tx(.01)
        with self.assertRaises(AssertionError):
            self.collect()
        with self.assertRaises(AssertionError):
            c.move(c.robot, c.env, **c.values)
        self.assertFalse(c.path.exists())
        c.runner.assert_not_called()


class EntryTests(unittest.TestCase):
    def test_both_entrypoints_install_and_restore_wiring_on_error(self):
        pairs = [(oc_runtime.Session, op_runtime_v2.Session),
            (oc_runtime.PreviewSession, op_runtime_v2.PreviewSession)]
        for revised, parent in pairs:
            with self.subTest(entry=revised.__name__):
                self.check_entry(revised, parent)

    def check_entry(self, revised, parent):
        before = (loop.plans, op_runtime.factory)
        def fail(_session):
            self.assertIs(oc_planning.plans, loop.plans)
            self.assertIs(oc_planning.factory, op_runtime.factory)
            raise ValueError('entry interrupted')
        with patch.object(parent, '_engine', fail):
            with self.assertRaisesRegex(ValueError, 'entry interrupted'):
                revised.__new__(revised)._engine()
        self.assertEqual(before, (loop.plans, op_runtime.factory))


if __name__ == '__main__':
    unittest.main(verbosity=2)

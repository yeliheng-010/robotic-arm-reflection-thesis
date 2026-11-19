"""阶段监测回归：抓取前和释放后环境碰撞必须中止。"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from reflection.monitors import ExecutionMonitor
from reflection.errors import TaskAbort, ErrorType


class MonitorTests(unittest.TestCase):
    def checked_tick(self, monitor):
        if os.environ.get('CHECK_ORIGINAL_MONITOR'):
            return ExecutionMonitor.tick(monitor)
        from stability.monitor import check_environment
        check_environment(monitor)
        return ExecutionMonitor.tick(monitor)

    def test_environment_collision_is_detected_in_every_phase(self):
        env = SimpleNamespace(mj_model=None, mj_data=None)
        for phase in ('idle', 'carry', 'release'):
            monitor = ExecutionMonitor(env, 'OrangeSphere', 'BlueBin')
            monitor.phase = phase
            with self.subTest(phase=phase), patch(
                    'reflection.monitors.held_object_contacts', return_value=[]), patch(
                    'reflection.monitors.robot_environment_contacts',
                    return_value=[('ur5e_base', 'SafetyDivider')]):
                with self.assertRaises(TaskAbort) as caught:
                    self.checked_tick(monitor)
                self.assertEqual(ErrorType.COLLISION, caught.exception.report.error_type)

    def test_clear_approach_does_not_require_target_already_held(self):
        monitor = ExecutionMonitor(SimpleNamespace(mj_model=None, mj_data=None), 'OrangeSphere', 'BlueBin')
        with patch('reflection.monitors.robot_environment_contacts', return_value=[]):
            self.checked_tick(monitor)
        self.assertEqual(0, monitor.missing_steps)

    def test_release_is_checked_even_if_legacy_scheduler_skips_tick(self):
        from reflection.__main__ import bootstrap
        bootstrap()
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
        from stability.monitor import guard_environment
        with patch.object(UR5GraspEnv, 'step', return_value=None), guard_environment():
            env = UR5GraspEnv(headless=True)
            monitor = ExecutionMonitor(env, 'OrangeSphere', 'BlueBin')
            monitor.phase = 'release'
            with patch('reflection.monitors.robot_environment_contacts',
                       return_value=[('ur5e_base', 'SafetyDivider')]):
                with self.assertRaises(TaskAbort):
                    env.step()


if __name__ == '__main__':
    unittest.main()


"""当前任务可见即可；其他任务遮挡不能导致无关拒绝。"""
import unittest
from sf_gate import accepted

PAIR = ('RedBlock', 'BlueBin')


class TaskGateTests(unittest.TestCase):
    def test_unrelated_occlusion_does_not_reject_current_task(self):
        visible = {name: dict(qualified=name in PAIR)
                   for name in (*PAIR, 'PurpleCapsule', 'RedBin')}
        self.assertTrue(accepted(dict(passed=True), visible, dict(passed=True), bodies=PAIR))

    def test_current_target_or_depth_or_framing_failure_rejects(self):
        visible = {name: dict(qualified=True) for name in PAIR}
        self.assertFalse(accepted(dict(passed=False), visible, dict(passed=True), bodies=PAIR))
        self.assertFalse(accepted(dict(passed=True), visible, dict(passed=False), bodies=PAIR))
        self.assertFalse(accepted(dict(passed=True), visible, None, bodies=PAIR))
        visible['BlueBin']['qualified'] = False
        self.assertFalse(accepted(dict(passed=True), visible, dict(passed=True), bodies=PAIR))


if __name__ == '__main__':
    unittest.main()

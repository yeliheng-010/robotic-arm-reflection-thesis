"""执行阶段来自嵌套语义上下文，不能误取顶层字段。"""
import unittest
from analyze import motion_phase


class MotionPhaseTests(unittest.TestCase):
    def test_uses_actual_nested_motion_phase(self):
        feedback = dict(stage='execution',evidence=dict(motion_context=dict(phase='carry_lift')))
        self.assertEqual('carry_lift',motion_phase(feedback))

    def test_no_fabricated_phase(self):
        self.assertIsNone(motion_phase(None))
        self.assertIsNone(motion_phase({'stage':'execution'}))


if __name__=='__main__':
    unittest.main()

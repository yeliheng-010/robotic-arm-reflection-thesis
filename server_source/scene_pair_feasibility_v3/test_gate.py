"""可见不等于传感器检查合格，失败视点应计入拒绝轨迹。"""
import importlib.util
import unittest


class GateTests(unittest.TestCase):
    def test_visible_but_failed_depth_check_is_rejected(self):
        self.assertIsNotNone(importlib.util.find_spec('sf_gate'), '缺少联合相机门禁')
        from sf_gate import accepted
        visible = {name: dict(qualified=True) for name in ('RedBlock','BlueBin','PurpleCapsule','RedBin')}
        self.assertFalse(accepted(dict(passed=True), visible, dict(passed=False)))
        self.assertTrue(accepted(dict(passed=True), visible, dict(passed=True)))
        visible['RedBlock']['qualified'] = False
        self.assertFalse(accepted(dict(passed=True), visible, dict(passed=True)))


if __name__ == '__main__':
    unittest.main()

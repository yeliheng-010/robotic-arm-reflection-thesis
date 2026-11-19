"""验证真正的拒绝边界与实验分母，不依赖GPU。"""
import unittest
from copy import deepcopy
from cc_policy import adopt, guarded_capture, paired_counts, VisibilityRejected


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(item=dict(group='varied_noisy'), config=dict(
            camera=dict(position=[1, 2, 3]), sensor=dict(dropout=.02), bodies={'box': [0, 0]}))

    def test_only_camera_changes_and_input_is_not_mutated(self):
        old = deepcopy(self.case)
        config = deepcopy(self.case['config'])
        config['camera']['position'] = [4, 5, 6]
        result = adopt(self.case, config)
        self.assertEqual(old, self.case)
        self.assertEqual(config, result['config'])
        result['config']['bodies']['box'][0] = 10
        self.assertEqual(old, self.case)

    def test_layout_or_noise_change_is_rejected(self):
        for key, value in [('bodies', {}), ('sensor', dict(dropout=0.))]:
            config = deepcopy(self.case['config'])
            config[key] = value
            with self.assertRaises(ValueError):
                adopt(self.case, config)

    def test_rejected_camera_never_falls_back(self):
        with self.assertRaises(ValueError):
            adopt(self.case, None)

    def test_baseline_change_is_rejected(self):
        self.case['item']['group'] = 'baseline'
        config = deepcopy(self.case['config'])
        config['camera']['position'] = [4, 5, 6]
        with self.assertRaises(ValueError):
            adopt(self.case, config)
        self.assertEqual(self.case, adopt(self.case, self.case['config']))

    def test_rejection_does_not_capture_or_publish(self):
        captured = []
        for result in [dict(accepted=False), dict(accepted=1), {}]:
            with self.assertRaises(VisibilityRejected):
                guarded_capture(lambda: result, lambda: captured.append('image'))
        self.assertEqual([], captured)

    def test_gate_precedes_each_capture(self):
        events = []
        def check():
            events.append('check')
            return dict(accepted=True)
        def capture():
            events.append('capture')
            return 'image'
        self.assertEqual('image', guarded_capture(check, capture))
        self.assertEqual('image', guarded_capture(check, capture))
        self.assertEqual(['check', 'capture', 'check', 'capture'], events)

    def test_unknown_audit_is_not_a_physical_failure(self):
        rows = [dict(qualified=False), dict(qualified=True, audit_passed=False,
                new_success=False, old_success=True), dict(qualified=True,
                audit_passed=True, new_success=True, old_success=False)]
        self.assertEqual(dict(registered=3, qualified=2, audited_pairs=1,
            new_successes=1, old_successes=0, improved=1, regressed=0,
            unknown=1, qualification_rejections=1), paired_counts(rows))


if __name__ == '__main__':
    unittest.main()

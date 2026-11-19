"""策略对照不允许悄悄改变场景、动作预算或分母。"""
import unittest
from copy import deepcopy
from ta_protocol import candidate, validate_pair, summarize


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(item=dict(seed=1, group='varied_noisy'), strategy='original',
            config=dict(camera={'position': [1, 2, 3]}, sensor={'dropout': .02}),
            state=dict(parameters=dict(time_scale=1.5, grasp_offset=[0., 0., 0.]), profile='original'),
            control=dict(grasp_mode='world_down'))

    def test_changes_only_strategy_without_mutating_source(self):
        before = deepcopy(self.case)
        new = candidate(self.case)
        self.assertEqual('observed_top', new['strategy'])
        self.assertEqual(before, self.case)
        self.assertTrue(validate_pair(self.case, new))
        new['config']['sensor']['dropout'] = 1
        self.assertEqual(before, self.case)

    def test_rejects_changed_camera_or_action_parameter(self):
        for field in ('config', 'state', 'item', 'control'):
            new = deepcopy(self.case)
            new['strategy'] = 'observed_top'
            new[field] = {}
            with self.assertRaises(ValueError):
                validate_pair(self.case, new)

    def test_rejects_wrong_strategy_or_nonzero_grasp_offset(self):
        with self.assertRaises(ValueError):
            validate_pair(self.case, self.case)
        self.case['state']['parameters']['grasp_offset'] = [0., 0., -.03]
        with self.assertRaises(ValueError):
            candidate(self.case)

    def test_no_per_seed_or_failure_based_selection(self):
        outputs = []
        for seed in (1, 2, 99):
            self.case['item']['seed'] = seed
            outputs.append(candidate(self.case)['strategy'])
        self.assertEqual(['observed_top']*3, outputs)

    def test_missing_or_unaudited_result_stays_unknown(self):
        rows = [dict(seed=1, audit_passed=True, new_success=True, old_success=False),
                dict(seed=2, audit_passed=False, new_success=False, old_success=True)]
        self.assertEqual(dict(registered=3, audited_pairs=1, unknown=2,
            new_successes=1, old_successes=0, improved=1, regressed=0), summarize(rows, (1, 2, 3)))

    def test_duplicate_and_foreign_seed_cannot_change_denominator(self):
        row = dict(seed=1, audit_passed=True, new_success=True, old_success=False)
        with self.assertRaises(ValueError):
            summarize([row, row], (1, 2))
        with self.assertRaises(ValueError):
            summarize([row], (2, 3))


if __name__ == '__main__':
    unittest.main()

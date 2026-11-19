"""配对身份、未知动作和已完成例必须分清。"""
import unittest
from pair_metrics import compare_pairs


def row(key, outcome, *, completed=False):
    return dict(input_id=key, snapshot_id='s'+key, completed=completed, model=outcome)


class PairTests(unittest.TestCase):
    def test_verified_improvement_and_regression(self):
        base = [row('a', 'observed_failure'), row('b', 'observed_success')]
        tuned = [row('a', 'observed_success'), row('b', 'stop_before_completion')]
        out = compare_pairs(base, tuned, seeds={'a': 1, 'b': 2})
        self.assertEqual(1, out['natural']['verified_improvements'])
        self.assertEqual(1, out['natural']['verified_regressions'])
        self.assertEqual(2, out['natural']['seed_groups'])

    def test_unknown_is_not_failure_or_improvement(self):
        base = [row('a', 'unmeasured_action'), row('b', 'observed_success')]
        tuned = [row('a', 'observed_success'), row('b', 'mixed_observed_outcomes')]
        out = compare_pairs(base, tuned, seeds={'a': 1, 'b': 1})
        self.assertEqual(0, out['natural']['verified_improvements'])
        self.assertEqual(0, out['natural']['verified_regressions'])
        self.assertEqual(1, out['natural']['seed_groups'])

    def test_completed_examples_separate(self):
        base = [row('a', 'completed_stop', completed=True)]
        out = compare_pairs(base, base, seeds={'a': 1})
        self.assertEqual(0, out['natural']['inputs'])
        self.assertEqual(1, out['completed']['inputs'])

    def test_missing_duplicate_or_mismatched_identity_rejected(self):
        base = [row('a', 'observed_failure')]
        variants = [[], base+base, [row('b', 'observed_failure')],
            [dict(base[0], snapshot_id='other')], [dict(base[0], completed=True)]]
        for tuned in variants:
            with self.subTest(tuned=tuned), self.assertRaises(AssertionError):
                compare_pairs(base, tuned, seeds={'a': 1})

    def test_unknown_category_rejected(self):
        base = [row('a', 'invented_success')]
        with self.assertRaises(AssertionError):
            compare_pairs(base, base, seeds={'a': 1})


if __name__ == '__main__':
    unittest.main()

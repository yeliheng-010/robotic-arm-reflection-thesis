import unittest
from pose_fresh_v1.evaluate import annotate, count, summarize
from pose_fresh_v1.common import contains_seed


def fit(center):
    return dict(center=center, axis=[1., 0., 0.])


class EvaluationTests(unittest.TestCase):
    def test_original_false_accept_is_not_hidden(self):
        row = dict(index=0, repeat=0, choice='original',
                   original=dict(fit=fit([.02, 0, 0]), quality_passed=True),
                   repaired=dict(fit=fit([0, 0, 0]), quality_passed=True))
        errors = annotate(dict(singles=[row], pairs=[]),
            [dict(index=0, full_frame_qualified=True)], dict(center=[0, 0, 0], axis=[1, 0, 0]))
        result = count(errors['singles'])
        self.assertEqual(1, result['selective']['false_accepted'])
        self.assertEqual(0, result['repair_new_false_accepts'])
        self.assertEqual(0, result['original_accepted_losses'])

    def test_repair_false_accept_is_private_but_counted(self):
        row = dict(index=0, repeat=0, choice='repaired',
                   original=dict(fit=None, quality_passed=False),
                   repaired=dict(fit=fit([.02, 0, 0]), quality_passed=True))
        errors = annotate(dict(singles=[row], pairs=[]),
            [dict(index=0, full_frame_qualified=False)], dict(center=[0, 0, 0], axis=[1, 0, 0]))
        result = summarize(errors)['singles']
        self.assertEqual(1, result['all_calibrated']['repair_new_false_accepts'])
        self.assertEqual(1, result['private_diagnostic']['repair_new_false_accepts'])
        self.assertEqual(0, result['qualified']['original']['observations'])

    def test_seed_scan_handles_nested_values_and_excludes_bool(self):
        self.assertTrue(contains_seed(dict(cases=[dict(seed=978101)]), {978101}))
        self.assertFalse(contains_seed(dict(enabled=True), {1}))


if __name__ == '__main__':
    unittest.main()

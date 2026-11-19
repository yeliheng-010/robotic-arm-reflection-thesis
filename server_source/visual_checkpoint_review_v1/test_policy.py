"""正式产物必须拒绝不完整训练、重复样本和不可信重载结果。"""
import copy
import unittest
import torch
from review_policy import validate_training, compare_logits


class ReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        self.settings = dict(train_samples=3, accumulation=2)
        self.result = dict(status='completed', samples_seen=3, updates=2,
            changed_tensors=2, test_used=False, manifest_sha256='frozen')
        self.updates = [dict(step=1, indices=[2, 0], samples=2, loss=1.,
            gradient_norm=2., supervised_tokens=20), dict(step=2, indices=[1],
            samples=1, loss=.8, gradient_norm=1., supervised_tokens=10)]

    def check(self, *, result=None, updates=None):
        validate_training(result or self.result, updates or self.updates,
            settings=self.settings, manifest_sha256='frozen')

    def test_complete_epoch_including_tail(self):
        self.check()

    def test_duplicate_or_missing_sample_rejected(self):
        updates = copy.deepcopy(self.updates)
        updates[1]['indices'] = [0]
        with self.assertRaises(AssertionError):
            self.check(updates=updates)
        with self.assertRaises(AssertionError):
            self.check(updates=self.updates[:1])

    def test_wrong_identity_or_no_change_rejected(self):
        for key, value in [('manifest_sha256', 'other'), ('changed_tensors', 0),
                ('test_used', True), ('status', 'failed')]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.check(result=dict(self.result, **{key: value}))

    def test_invalid_update_rejected(self):
        for key, value in [('loss', float('nan')), ('gradient_norm', 0.),
                ('supervised_tokens', 0), ('samples', 1), ('step', 2)]:
            updates = copy.deepcopy(self.updates)
            updates[0][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.check(updates=updates)

    def test_reload_tolerance_and_finiteness(self):
        expected = torch.tensor([.1, .2, .3])
        self.assertEqual(0., compare_logits(expected, expected.clone()))
        for actual in [expected + .01, torch.tensor([float('nan')]*3),
                torch.tensor([float('inf')]*3), expected[:2]]:
            with self.assertRaises(AssertionError):
                compare_logits(expected, actual)


if __name__ == '__main__':
    unittest.main()

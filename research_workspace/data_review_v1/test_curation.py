"""防止泄漏、冲突标签及来源丢失。"""
import unittest
from curation import curate, verify_groups


def sample(identity, *, split='train', source='rule', target='a', seed=1):
    return dict(uid=identity, input_hash='same', target=target, split=split,
                source=source, batch='batch', seed=seed, messages=[])


class CurationTests(unittest.TestCase):
    def test_group_leak_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_groups([sample('a'), sample('b', split='dev')])

    def test_provenance_preserved_when_deduplicating(self):
        kept, rejected = curate([sample('a'), sample('b', source='hybrid')])
        self.assertEqual(1, len(kept))
        self.assertEqual(['a', 'b'], kept[0]['members'])
        self.assertEqual(['hybrid', 'rule'], kept[0]['sources'])
        self.assertEqual([], rejected)

    def test_conflicting_targets_are_quarantined(self):
        kept, rejected = curate([sample('a'), sample('b', target='b')])
        self.assertEqual([], kept)
        self.assertEqual(2, len(rejected))
        self.assertTrue(all(r['reason']=='ambiguous_target' for r in rejected))

    def test_eval_overlap_is_removed_from_training(self):
        kept, rejected = curate([sample('a'), sample('b', split='dev', seed=2)])
        self.assertEqual(['dev'], [r['split'] for r in kept])
        self.assertEqual('eval_overlap', rejected[0]['reason'])

    def test_different_inputs_are_not_merged(self):
        other = dict(sample('b'), input_hash='different')
        kept, rejected = curate([sample('a'), other])
        self.assertEqual(2, len(kept))
        self.assertEqual([], rejected)


if __name__ == '__main__':
    unittest.main()

import unittest
from collection_common import seeds, split, action, MAX_BATCHES, BRANCHES


class ProtocolTests(unittest.TestCase):
    def test_disjoint_seed_groups_and_split(self):
        groups = [seeds(i) for i in range(MAX_BATCHES)]
        self.assertEqual(32*MAX_BATCHES, len(set(sum(groups, ()))))
        for group in groups:
            self.assertEqual(24, sum(split(s)=='train' for s in group))
            self.assertEqual(8, sum(split(s)=='dev' for s in group))

    def test_actions_frozen_independent_of_observed_error(self):
        expected = [('SET_GRASP_STRATEGY','SET_TIME_SCALE'), ('SET_GRASP_OFFSET','SET_TIME_SCALE'),
            ('SET_TIME_SCALE','SET_GRASP_STRATEGY')]
        self.assertEqual(expected, [tuple(action(b,i)['id'] for i in range(2)) for b in BRANCHES])
        with self.assertRaises(AssertionError):
            action(BRANCHES[0],2)


if __name__ == '__main__':
    unittest.main()

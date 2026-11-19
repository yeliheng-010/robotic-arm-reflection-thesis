import unittest
from rc_gate import summarize, assess


def row(index, split='train', action='SET_GRASP_STRATEGY', recovered=True):
    return dict(snapshot_id=str(index), seed=index//4, split=split, source='block' if index%2 else 'capsule',
        eligible_natural=True, verified_recovery=recovered, action=dict(id=action, args={}))


class GateTests(unittest.TestCase):
    def test_shared_frames_and_branches_count_once(self):
        value = row(1)
        self.assertEqual(1, summarize([value]*6)['train']['snapshots'])
        self.assertEqual(1, summarize([value]*6)['train']['recoveries'])

    def test_planning_rejections_are_excluded(self):
        value = dict(row(1), eligible_natural=False, verified_recovery=False)
        self.assertEqual(0, summarize([value])['train']['snapshots'])

    def test_seed_split_leakage_rejected(self):
        with self.assertRaises(AssertionError):
            summarize([row(1), row(2, split='dev')])

    def test_snapshot_split_leakage_rejected(self):
        with self.assertRaises(AssertionError):
            summarize([row(1), dict(row(1, split='dev'), seed=999)])

    def test_one_action_cannot_open_gate(self):
        rows = [row(i) for i in range(120)]+[row(i, split='dev') for i in range(1000,1040)]
        self.assertFalse(assess(summarize(rows))['quantitative_ready'])

    def test_full_minimum_and_independent_learning_evidence(self):
        rows = [row(i, action='SET_TIME_SCALE' if i%2 else 'SET_GRASP_STRATEGY') for i in range(120)]
        rows += [row(i, split='dev') for i in range(1000,1040)]
        result = assess(summarize(rows))
        self.assertTrue(result['quantitative_ready'])
        self.assertFalse(result['training_ready'])


if __name__ == '__main__':
    unittest.main()

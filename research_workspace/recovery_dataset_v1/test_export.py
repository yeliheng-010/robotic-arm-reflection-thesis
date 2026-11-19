import unittest
from export_records import deduplicate, select_training, record, outcome


def example(index, kind='verified_recovery', action='SET_GRASP_STRATEGY'):
    return dict(input_id=str(index), snapshot_id=str(index), seed=index, split='train', kind=kind,
        action=dict(id=action,args={}))


class ExportTests(unittest.TestCase):
    def test_stop_requires_actual_completed_input(self):
        request = dict(evidence=[dict(field='execution_facts',value=dict(task_completed=False))])
        with self.assertRaises(AssertionError):
            outcome(request,dict(action=dict(id='STOP',args={})),stop=True)

    def test_recovery_requires_immediate_successful_successor(self):
        request = dict(evidence=[dict(field='execution_facts',value=dict(task_completed=False))])
        row = dict(before=dict(index=1,success=False),successor=dict(index=3,success=True),
            action=dict(id='SET_TIME_SCALE',args=dict(value=3.)))
        with self.assertRaises(AssertionError):
            outcome(request,row,stop=False)
    def test_failures_cannot_be_positive_targets(self):
        with self.assertRaises(AssertionError):
            record(dict(eligible_natural=True, verified_recovery=False))

    def test_multiple_successful_actions_not_unique_optimum(self):
        rows = deduplicate([example(1), example(1,action='SET_TIME_SCALE')])
        self.assertEqual(1,len(rows))
        self.assertEqual(2,len(rows[0]['accepted_actions']))

    def test_same_input_cannot_cross_splits(self):
        with self.assertRaises(AssertionError):
            deduplicate([example(1), dict(example(1),split='dev')])

    def test_identical_baseline_across_seeds_is_not_repeated(self):
        self.assertEqual(1,len(deduplicate([example(1), dict(example(1),seed=2)])))

    def test_stop_samples_cannot_dominate(self):
        rows = [example(i) for i in range(4)]+[example(i,'completed_stop') for i in range(10,30)]
        selected = select_training(rows)
        self.assertEqual(6,len(selected))
        self.assertEqual(2,sum(r['kind']=='completed_stop' for r in selected))


if __name__ == '__main__':
    unittest.main()

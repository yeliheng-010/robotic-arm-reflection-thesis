import copy
import unittest
from coverage_stats import coverage, task_counts, validate_rows


def case(seed=1, task='RedBlock', split='train'):
    return dict(item=dict(id=f'{seed}_{task}', seed=seed, source=task,
        split=split, group='varied_noisy'), config=dict(camera=dict(
        azimuth_offset_deg=0., elevation_deg=50., distance_m=1.2, fovy=55.),
        bodies={'BlueBin': dict(position=[1., .5, .74])},
        appearance={'BlueBin': dict(color='blue')},
        sensor=dict(depth_sigma_m=.003, dropout=.02)))


def row(snapshot='a', recovered=False):
    return dict(condition='1_RedBlock', snapshot_id=snapshot, seed=1,
        source='RedBlock', split='train', eligible_natural=True,
        verified_recovery=recovered)


class CoverageTests(unittest.TestCase):
    def test_shared_branches_do_not_expand_snapshots(self):
        actual = task_counts([row(), row(recovered=True), row('b')])['train']['RedBlock']
        self.assertEqual(dict(snapshots=2, seeds=1, recoveries=1, recovery_seeds=1), actual)

    def test_tasks_share_environment_but_not_condition(self):
        values = [case(), case(task='PurpleCapsule')]
        actual = coverage(values)
        self.assertEqual(1, actual['seed_groups'])
        self.assertEqual(2, actual['conditions'])
        self.assertEqual(1, sum(actual['camera']['azimuth_offset_deg']['histogram']))

    def test_cross_split_or_wrong_task_rejected(self):
        original = row()
        for key, value in [('split', 'dev'), ('source', 'PurpleCapsule'), ('seed', 2)]:
            broken = dict(original, **{key: value})
            with self.assertRaises(AssertionError):
                validate_rows([case()], [broken])
        with self.assertRaises(AssertionError):
            validate_rows([case(), case(task='PurpleCapsule', split='dev')], [])

    def test_shared_seed_cannot_have_different_environment(self):
        other = case(task='PurpleCapsule')
        other['config']['camera']['distance_m'] = 1.3
        with self.assertRaises(AssertionError):
            coverage([case(), other])

    def test_noise_and_recovery_without_natural_rejected(self):
        other = copy.deepcopy(case())
        other['config']['sensor']['dropout'] = 0.
        with self.assertRaises(AssertionError):
            coverage([other])
        with self.assertRaises(AssertionError):
            validate_rows([case()], [dict(row(recovered=True), eligible_natural=False)])

    def test_empty_subset_and_noneligible_not_counted(self):
        self.assertEqual(0, coverage([])['seed_groups'])
        self.assertEqual({}, task_counts([dict(row(), eligible_natural=False)])['train'])


if __name__ == '__main__':
    unittest.main()

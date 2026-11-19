import unittest
from copy import deepcopy
from vd_collect import summarize


def row(**changes):
    value = dict(snapshot_id='one', seed=1, source='Block', eligible_natural=True, verified_recovery=False,
        private_eligibility_reason='natural_execution_or_perception_failure', status='proposed',
        action=dict(id='OBSERVE', args={}))
    value.update(changes)
    return value


class DataAccountingTests(unittest.TestCase):
    def test_shared_snapshot_and_observations_do_not_inflate(self):
        values = [row(), row(), row()]
        result = summarize(values)
        self.assertEqual(1, result['unique_natural_snapshots'])
        self.assertEqual(0, result['verified_natural_recoveries'])
        self.assertFalse(result['training_ready'])

    def test_planning_recovery_excluded_and_natural_recovery_deduplicated(self):
        action = dict(id='SET_GRASP_STRATEGY', args=dict(value='observed_top'))
        good = row(action=action, verified_recovery=True)
        engineering = row(snapshot_id='two', eligible_natural=False, verified_recovery=True,
            private_eligibility_reason='planning_rejection', action=action)
        result = summarize([good, deepcopy(good), engineering])
        self.assertEqual(1, result['verified_natural_recoveries'])
        self.assertEqual(['SET_GRASP_STRATEGY'], result['correction_action_types'])
        self.assertEqual({'planning_rejection':1}, result['exclusions'])

    def test_invalid_output_is_not_a_supervised_action(self):
        result = summarize([row(action=None, status='invalid_output')])
        self.assertEqual({}, result['action_counts'])
        self.assertEqual({'invalid_output':1}, result['decision_statuses'])
        self.assertEqual(0, result['verified_natural_recoveries'])

from copy import deepcopy
import unittest
from public_execution import public


class FactsTests(unittest.TestCase):
    def fixture(self):
        step = dict(index=1, success=False, state=dict(parameters=dict(time_scale=1)))
        row = dict(action='move_to_grasp_pose', executed=True, result=dict(feasible=True),
                   durations=[0, 1], start_time=2, end_time=2.4)
        return step, dict(requested=dict(time_scale=1), planners=[row])

    def test_partial_motion_is_reported_as_started_not_completed(self):
        step, bridge = self.fixture()
        value = public(step, bridge)
        self.assertFalse(value['task_completed'])
        self.assertTrue(value['command_execution'][0]['motion_started'])
        self.assertAlmostEqual(.4, value['command_execution'][0]['elapsed_s'])
        self.assertNotIn('motion_completed', value['command_execution'][0])

    def test_hidden_labels_and_future_fields_have_no_effect(self):
        step, bridge = self.fixture()
        before = public(step, bridge)
        step['future_success'] = True
        bridge['diagnosis'] = 'SECRET_CAUSE'
        bridge['planners'][0]['result']['failure'] = dict(reason='SECRET_CAUSE')
        self.assertEqual(before, public(step, bridge))

    def test_rejected_plan_does_not_invent_execution_time(self):
        step, bridge = self.fixture()
        row = bridge['planners'][0]
        row.update(executed=False, result=dict(feasible=False))
        row.pop('start_time')
        row.pop('end_time')
        value = public(step, bridge)['command_execution'][0]
        self.assertFalse(value['geometry_admitted'])
        self.assertIsNone(value['elapsed_s'])

    def test_bad_time_or_contradictory_state_rejected(self):
        step, bridge = self.fixture()
        bad = deepcopy(bridge)
        bad['planners'][0]['end_time'] = 1
        with self.assertRaises(AssertionError):
            public(step, bad)
        bridge['planners'][0]['result']['feasible'] = False
        with self.assertRaises(AssertionError):
            public(step, bridge)


if __name__ == '__main__':
    unittest.main()

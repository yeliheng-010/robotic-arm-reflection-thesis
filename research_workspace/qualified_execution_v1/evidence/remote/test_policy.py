import unittest
from qualified_execution_v1 import policy


class ExecutionPolicyTests(unittest.TestCase):
    def test_all_initial_guards_required(self):
        values = dict(initial_qualified=True, state_matches=True, preflight_passed=True, audit_passed=True)
        self.assertTrue(policy.initial_allowed(**values))
        for key in values:
            self.assertFalse(policy.initial_allowed(**dict(values, **{key: False})))

    def test_unqualified_frame_never_published(self):
        self.assertEqual('stop_without_model_input', policy.observation_action(requested=True, qualified=False))
        self.assertEqual('stop_without_model_input', policy.observation_action(requested=True, qualified=None))
        self.assertEqual('publish_qualified', policy.observation_action(requested=True, qualified=True))

    def test_no_observation_does_not_become_qualified(self):
        self.assertEqual('no_model_observation', policy.observation_action(requested=False, qualified=False))

    def test_placement_after_abort_not_task_success(self):
        self.assertFalse(policy.accepted(completed=False, physical_placement=True, safety_error='collision'))
        self.assertFalse(policy.accepted(completed=True, physical_placement=True, safety_error='tracking'))
        self.assertTrue(policy.accepted(completed=True, physical_placement=True, safety_error=None))


if __name__ == '__main__':
    unittest.main()

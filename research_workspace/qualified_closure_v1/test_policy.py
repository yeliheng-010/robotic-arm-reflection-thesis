import unittest
from qualified_closure_v1.policy import summarize, public_feedback


class PolicyTests(unittest.TestCase):
    def test_middle_collision_rejects_even_with_clear_endpoints(self):
        rows = [dict(valid=True, contacts=[]),
                dict(valid=True, contacts=[dict(roots=['2f85_base', 'SortingTray'])]),
                dict(valid=True, contacts=[])]
        result = summarize(rows, expected_count=3)
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['first_rejected_index'])

    def test_clear_complete_samples_pass_static_gate_only(self):
        result = summarize([dict(valid=True, contacts=[])], expected_count=1)
        self.assertTrue(result['passed'])
        self.assertFalse(result['dynamic_safety_proven'])

    def test_invalid_or_incomplete_evidence_rejects(self):
        for rows in ([], [dict(valid=False, contacts=[])], [dict(contacts=[])]):
            with self.subTest(rows=rows):
                self.assertFalse(summarize(rows, expected_count=1)['passed'])

    def test_private_geometry_cannot_enter_public_feedback(self):
        result = summarize([dict(valid=True, contacts=[dict(private_position=[1, 2, 3])])],
                           expected_count=1)
        self.assertEqual(dict(status='rejected', stage='gripper_closure'), public_feedback(result))


if __name__ == '__main__':
    unittest.main()

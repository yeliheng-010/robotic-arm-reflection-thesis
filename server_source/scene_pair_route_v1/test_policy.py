import unittest
from route_policy import eligible, first_feasible


class PolicyTests(unittest.TestCase):
    def test_destination_contact_triggers(self):
        for root in ('ur5e_base', '2f85_base'):
            self.assertTrue(eligible(dict(error_type='collision', evidence={'contacts': [[root, 'BlueBin']]}), 'BlueBin'))

    def test_unrelated_or_missing_feedback_is_unchanged(self):
        for report in (None, {}, dict(error_type='object_dropped'),
                       dict(error_type='collision', evidence={'contacts': [['2f85_base', 'Knife']]})):
            self.assertFalse(eligible(report, 'BlueBin'))

    def test_first_feasible_and_exclusion(self):
        rows = [dict(id='a', feasible=False), dict(id='b', feasible=True), dict(id='c', feasible=True)]
        self.assertEqual('b', first_feasible(rows, set())['id'])
        self.assertEqual('c', first_feasible(rows, {'b'})['id'])
        self.assertIsNone(first_feasible(rows, {'b', 'c'}))


if __name__ == '__main__':
    unittest.main()

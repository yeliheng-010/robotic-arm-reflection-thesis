import unittest
from ig_policy import execution_mode, audit_disposition


class PolicyTests(unittest.TestCase):
    def test_never_reexecute_consumed_cases(self):
        self.assertEqual('execute_new', execution_mode(folder_exists=False, completed=False))
        self.assertEqual('audit_existing', execution_mode(folder_exists=True, completed=True))
        with self.assertRaises(AssertionError):
            execution_mode(folder_exists=True, completed=False)

    def test_any_self_contact_quarantines_whole_condition(self):
        self.assertEqual('audit', audit_disposition([0, 0, 0]))
        self.assertEqual('quarantine', audit_disposition([0, 1, 0]))
        self.assertEqual('quarantine', audit_disposition([2]))


if __name__ == '__main__':
    unittest.main()

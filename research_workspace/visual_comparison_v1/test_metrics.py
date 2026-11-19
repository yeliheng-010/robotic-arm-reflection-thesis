import unittest
from vc_metrics import classify


def action(name):
    return dict(id=name, args={})


class MetricsTests(unittest.TestCase):
    def test_all_successful_alternatives_accepted(self):
        rows = [dict(action=action(n), success=True) for n in ('A', 'B')]
        for n in ('A', 'B'):
            self.assertEqual('observed_success', classify(action(n), rows, valid=True))

    def test_unknown_is_not_failure(self):
        self.assertEqual('unmeasured_action', classify(action('C'), [], valid=True))

    def test_conflicting_repeated_outcomes_not_hidden(self):
        rows = [dict(action=action('A'), success=s) for s in (True, False)]
        self.assertEqual('mixed_observed_outcomes', classify(action('A'), rows, valid=True))

    def test_stop_depends_on_task_completion(self):
        self.assertEqual('stop_before_completion', classify(action('STOP'), [], valid=True))
        self.assertEqual('completed_stop', classify(action('STOP'), [], valid=True, completed=True))

    def test_invalid_has_priority(self):
        self.assertEqual('invalid_output', classify(None, [], valid=False))

    def test_numeric_json_spellings_are_equivalent(self):
        chosen = dict(id='SET_TIME_SCALE', args=dict(value=3))
        rows = [dict(action=dict(id='SET_TIME_SCALE', args=dict(value=3.0)), success=True)]
        self.assertEqual('observed_success', classify(chosen, rows, valid=True))


if __name__ == '__main__':
    unittest.main()

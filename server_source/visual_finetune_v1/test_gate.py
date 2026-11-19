import unittest
from vf_gate import check_ready


def fixtures(category='observed_failure'):
    rows = [dict(input_id=str(i), snapshot_id=str(i), model=category) for i in range(3)]
    private = [dict(input_id=str(i), snapshot_id=str(i), seed=i, completed=False,
        outcomes=[dict(success=True)]) for i in range(3)]
    return (dict(gate=dict(quantitative_ready=True)), dict(passed=True, quantitative_ready=True),
        dict(rows=rows, inputs=3, model_calls=3, physical_attempts=0, training_updates=0), private)


class ReadyTests(unittest.TestCase):
    def test_original_gate_required(self):
        dataset, audit, report, private = fixtures()
        dataset['gate']['quantitative_ready'] = False
        with self.assertRaises(AssertionError):
            check_ready(dataset, audit, report, private)

    def test_unknown_actions_not_declared_defects(self):
        with self.assertRaises(AssertionError):
            check_ready(*fixtures('unmeasured_action'))

    def test_repeated_seed_cannot_fake_support(self):
        dataset, audit, report, private = fixtures()
        for row in private:
            row['seed'] = 1
        with self.assertRaises(AssertionError):
            check_ready(dataset, audit, report, private)

    def test_requires_a_real_successful_alternative(self):
        dataset, audit, report, private = fixtures()
        private[0]['outcomes'] = [dict(success=False)]
        with self.assertRaises(AssertionError):
            check_ready(dataset, audit, report, private)

    def test_evidence_allows_controlled_trial(self):
        result = check_ready(*fixtures())
        self.assertEqual(3, result['defect_seed_groups'])


if __name__ == '__main__':
    unittest.main()

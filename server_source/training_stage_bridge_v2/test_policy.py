import unittest
from policy import decide


class BridgeTests(unittest.TestCase):
    def test_count_gate_only_starts_preparation(self):
        self.assertEqual('stage_preparation', decide(dict(gate=dict(quantitative_ready=True)), None))

    def test_stalled_collection_requires_development_not_training(self):
        self.assertEqual('development_required', decide(dict(gate=dict(quantitative_ready=False)),
            dict(advance=False, reason='natural_failure_task_coverage_requires_development')))

    def test_incomplete_data_keeps_waiting(self):
        self.assertEqual('collecting', decide(None, None))
        self.assertEqual('collecting', decide(dict(gate=dict(quantitative_ready=False)), dict(advance=True)))


if __name__ == '__main__':
    unittest.main()

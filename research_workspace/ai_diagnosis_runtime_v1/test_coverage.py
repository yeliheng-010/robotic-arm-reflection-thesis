from copy import deepcopy
import unittest
from coverage_gate import evaluate


def row():
    return dict(id='example_varied_noisy', success=False,
                motion=dict(actual_motion=True, grasp_checked=True, carry_checked=True),
                observation=dict(frames=3, extra=2), lifecycle=dict(evidence='runtime_event'),
                model_input=dict(actions=['STOP', 'RETRY']))


class CoverageTests(unittest.TestCase):
    def test_all_success_does_not_prove_failure_observation(self):
        value = row()
        value.update(success=True, observation=dict(frames=1, extra=0), model_input=dict(actions=['STOP']))
        self.assertFalse(evaluate([value])['model_smoke_gate'])

    def test_failure_without_repeated_frames_still_blocks(self):
        value = row()
        value['observation'] = dict(frames=1, extra=0)
        self.assertFalse(evaluate([value])['model_smoke_gate'])

    def test_gate_requires_all_coverage_fields(self):
        value = row()
        self.assertTrue(evaluate([value])['model_smoke_gate'])
        changed = deepcopy(value)
        changed['lifecycle']['evidence'] = 'inferred'
        self.assertFalse(evaluate([changed])['model_smoke_gate'])


if __name__ == '__main__':
    unittest.main()

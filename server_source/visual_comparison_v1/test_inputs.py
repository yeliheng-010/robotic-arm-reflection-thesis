import unittest
from unittest.mock import patch
from vc_inputs import collect


def sample(**extra):
    value = dict(split='dev', eligible_natural=True, input_path='input', input_sha256='hash',
        snapshot_id='snapshot', seed=1, action=dict(id='SET_TIME_SCALE', args=dict(value=3)),
        successor=dict(success=False))
    value.update(extra)
    return value


class InputTests(unittest.TestCase):
    @patch('vc_inputs.build', return_value=dict(input_id='one', request={}))
    def test_train_and_planning_rejection_never_enter(self, build):
        rows = [sample(), sample(split='train'), sample(eligible_natural=False)]
        inputs, private = collect(rows, [])
        self.assertEqual(1, build.call_count)
        self.assertEqual(1, len(inputs))
        self.assertEqual(1, len(private[0]['outcomes']))
        self.assertNotIn('outcomes', inputs[0])

    @patch('vc_inputs.build', return_value=dict(input_id='one', request={}))
    def test_shared_input_keeps_both_observed_outcomes(self, build):
        inputs, private = collect([sample(), sample(successor=dict(success=True))], [])
        self.assertEqual(1, len(inputs))
        self.assertEqual([False, True], [r['success'] for r in private[0]['outcomes']])

    @patch('vc_inputs.build', return_value=dict(input_id='one', request={}))
    def test_same_input_different_snapshot_refused(self, build):
        with self.assertRaises(AssertionError):
            collect([sample(), sample(snapshot_id='different')], [])


if __name__ == '__main__':
    unittest.main()

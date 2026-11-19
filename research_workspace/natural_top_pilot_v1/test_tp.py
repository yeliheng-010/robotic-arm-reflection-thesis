import unittest
from loopstudy.actions import initial
from sr_common import change as setup
from tp_common import change, ACTIONS


class StrategyTests(unittest.TestCase):
    def test_explicit_strategy_then_slow_and_original_immutable(self):
        state, _ = setup(initial(), dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        state['parameters']['lift_height'] = .20
        next_state, strategy = change(state, 'original', action=ACTIONS[0])
        self.assertEqual(state, next_state)
        self.assertEqual('observed_top', strategy)
        slow, strategy = change(next_state, strategy, action=ACTIONS[1])
        self.assertEqual(3., slow['parameters']['time_scale'])
        self.assertEqual(1.5, state['parameters']['time_scale'])
        self.assertEqual([0.,0.,0.], slow['parameters']['grasp_offset'])

    def test_illegal_order_and_offset_mix_rejected(self):
        state, _ = setup(initial(), dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        with self.assertRaises(AssertionError):
            change(state, 'original', action=ACTIONS[1])
        state['parameters']['grasp_offset'] = [0.,0.,-.03]
        with self.assertRaises(AssertionError):
            change(state, 'original', action=ACTIONS[0])

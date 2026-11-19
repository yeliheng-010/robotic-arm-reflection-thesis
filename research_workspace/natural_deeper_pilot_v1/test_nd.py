import unittest
from loopstudy.actions import initial
from sr_common import change as setup
from nd_common import change, ACTIONS


class DeeperTests(unittest.TestCase):
    def test_commands_and_immutability(self):
        state, control = setup(initial(), dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        deeper, _ = change(state, control, action=ACTIONS[0])
        self.assertEqual([0., 0., 0.], state['parameters']['grasp_offset'])
        self.assertEqual([0., 0., -.03], deeper['parameters']['grasp_offset'])
        slow, _ = change(deeper, control, action=ACTIONS[1])
        self.assertEqual(3., slow['parameters']['time_scale'])
        self.assertEqual([0., 0., -.03], slow['parameters']['grasp_offset'])

    def test_order_and_unsupported_action_rejected(self):
        state, control = setup(initial(), dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        with self.assertRaises(AssertionError):
            change(state, control, action=ACTIONS[1])
        with self.assertRaises(ValueError):
            change(state, control, action='REGROUND')

import unittest
from loopstudy.actions import initial
from sr_common import change, ACTIONS


class ActionTests(unittest.TestCase):
    def test_registered_sequence_and_original_preserved(self):
        state, control = initial(), dict(grasp_mode='original')
        safe, down = change(state, control, action=ACTIONS[0])
        lower, _ = change(safe, down, action=ACTIONS[1])
        self.assertEqual(False, state['parameters']['replan'])
        self.assertEqual('original', control['grasp_mode'])
        self.assertEqual(.15, safe['parameters']['lift_height'])
        self.assertEqual(1.5, safe['parameters']['time_scale'])
        self.assertEqual([0., 0., -.015], lower['parameters']['grasp_offset'])

    def test_unregistered_and_out_of_order_rejected(self):
        with self.assertRaises(ValueError):
            change(initial(), dict(grasp_mode='original'), action='FOURTH_ATTEMPT')
        with self.assertRaises(AssertionError):
            change(initial(), dict(grasp_mode='original'), action=ACTIONS[1])


if __name__ == '__main__':
    unittest.main()

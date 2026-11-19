import unittest
from loopstudy.actions import initial
from sr_common import change as safe
from qp_common import change,ACTIONS


class ActionTests(unittest.TestCase):
    def test_both_actions_preserve_safe_execution(self):
        state,control=safe(initial(),dict(grasp_mode='original'),action='SELF_SAFE_ROUTE')
        lower,selected=change(state,control,action=ACTIONS[0])
        slow,_=change(lower,selected,action=ACTIONS[1])
        self.assertEqual([0.,0.,-.01],lower['parameters']['grasp_offset'])
        self.assertEqual(3.,slow['parameters']['time_scale'])
        self.assertEqual(.15,slow['parameters']['lift_height'])
        self.assertEqual(True,slow['parameters']['replan'])
        self.assertEqual([0.,0.,0.],state['parameters']['grasp_offset'])

    def test_unknown_action_rejected(self):
        state,control=safe(initial(),dict(grasp_mode='original'),action='SELF_SAFE_ROUTE')
        with self.assertRaises(ValueError):
            change(state,control,action='FOURTH_ATTEMPT')


if __name__=='__main__':
    unittest.main()

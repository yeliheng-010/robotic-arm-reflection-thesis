import unittest
from core import same_input,summarize


class Tests(unittest.TestCase):
    def test_equal_success_cannot_substitute_input_equality(self):
        a=dict(before={'offset':1},feedback={},candidates=[])
        b=dict(a,before={'offset':2})
        self.assertFalse(same_input(a,b))

    def test_same_kind_not_same_action(self):
        a={'kind':'measured_grasp','changes':{'offset':1}}
        b={'kind':'measured_grasp','changes':{'offset':2}}
        self.assertEqual(a['kind'],b['kind'])
        self.assertNotEqual(a,b)

    def test_candidate_order_is_input(self):
        a=dict(before={},feedback={},candidates=[1,2])
        self.assertFalse(same_input(a,dict(a,candidates=[2,1])))

    def test_no_decisions_not_successful_choices(self):
        self.assertEqual(0,summarize([])['decisions'])


if __name__=='__main__':
    unittest.main()

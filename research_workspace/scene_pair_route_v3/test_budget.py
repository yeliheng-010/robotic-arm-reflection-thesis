import unittest
from reflection.__main__ import bootstrap
bootstrap()
from goal_search import budget_expired,compatible


class BudgetTests(unittest.TestCase):
    def test_search_stops_at_either_budget(self):
        self.assertFalse(budget_expired([None]*255,[None]*511))
        self.assertTrue(budget_expired([None]*256,[]))
        self.assertTrue(budget_expired([],[None]*512))

    def test_pose_and_branch_must_both_match(self):
        endpoint=dict(ok=True,pose='world_down_-135',config=[1,-1,1])
        option=dict(id='world_down_-135_0.1_1,-1,1',rise=.1)
        self.assertEqual([endpoint],compatible(option,{'config':[1,-1,1]},{'goals':[endpoint]}))
        self.assertEqual([],compatible(option,{'config':[1,1,1]},{'goals':[endpoint]}))


if __name__=='__main__':
    unittest.main()

"""计入非法/失败分支；配对不把补看次数当独立样本。"""
import unittest
from od_metrics import summarize
from od_common import SELECTORS,LEVELS


class MetricTests(unittest.TestCase):
    def test_both_paired_directions_and_cost(self):
        rows=[]
        for flags in ((False,True,False),(True,False,True)):
            outcomes=[dict(selector=s,level=n,success=flags[n],attempted=True,extra_observations=n)
                for n in LEVELS for s in SELECTORS]
            rows.append(dict(outcomes=outcomes))
        value=summarize(rows)
        self.assertEqual({'observe_only':1,'direct_only':1},value['paired']['model_l0_vs_l1'])
        self.assertEqual(4,value['arms']['rule_l2']['extra_observations'])
        self.assertEqual(2,value['arms']['rule_l2']['snapshots'])

    def test_invalid_is_not_dropped(self):
        rows=[dict(outcomes=[dict(selector=s,level=n,success=False,attempted=False,extra_observations=n)
                for n in LEVELS for s in SELECTORS])]
        value=summarize(rows)
        self.assertEqual(1,value['arms']['model_l0']['snapshots'])
        self.assertEqual(0,value['arms']['model_l0']['executions'])


if __name__=='__main__':
    unittest.main()

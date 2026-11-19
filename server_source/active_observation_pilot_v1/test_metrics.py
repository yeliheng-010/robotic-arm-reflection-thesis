import unittest
from ap_metrics import prefix,analyze,curves
from ap_common import METHODS


class MetricTests(unittest.TestCase):
    def test_budget_one_has_no_future_fee(self):
        t={'attempts':[{'success':False},{'success':True}],
           'decisions':[{'after_attempt':1,'observation':{'extra_cost':2}}]}
        self.assertEqual(0,prefix(t,1)['extra_observations'])
        self.assertEqual(2,prefix(t,3)['attempts'])

    def test_skip_not_observed_failure(self):
        value={'scene':{'id':'skip','seed':1,'factor':'grasp_bias'},'eligible':False,'trajectories':[]}
        r=analyze([value],lambda _:None)
        self.assertEqual((1,0,1),(r['curves'][0]['planned'],r['curves'][0]['executed'],r['curves'][0]['skipped']))
        self.assertEqual({},r['curves'][0]['paired'])

    def test_both_directions_are_retained(self):
        rows=[]
        for i in (0,1):
            methods={m:{str(b):dict(success=(j==i),first_success=False,attempts=2,extra_observations=1)
                        for b in (1,2,3)} for j,m in enumerate(METHODS)}
            rows.append(dict(eligible=True,methods=methods))
        self.assertEqual({'fixed_only':1,'adaptive_only':1},curves(rows)[1]['paired'])


if __name__=='__main__':
    unittest.main()

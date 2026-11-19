"""预算费用与失败/跳过分母的回归验证。"""
import unittest
from om_metrics import prefix,analyze
from om_common import METHODS
from om_compare import semantic


def trace():
    return dict(attempts=[{'success':False},{'success':True}],decisions=[dict(after_attempt=1,
        observation={'extra_cost':2},event={'elapsed_s':.1,'response':{'usage':{'prompt_tokens':5,'completion_tokens':3}}})])


class MetricTests(unittest.TestCase):
    def test_budget_one_has_no_future_observation_or_model_charge(self):
        r=prefix(trace(),1)
        self.assertEqual((0,0,0),(r['model_calls'],r['extra_observations'],r['prompt_tokens']))

    def test_success_stops_and_no_padding(self):
        r=prefix(trace(),3)
        self.assertEqual((2,1,2),(r['attempts'],r['model_calls'],r['extra_observations']))

    def test_invalid_without_execution_is_charged(self):
        t=trace()
        t['attempts']=t['attempts'][:1]
        t['decisions'][0]['invalid']='bad JSON'
        r=prefix(t,2)
        self.assertEqual((False,1,1,2),(r['success'],r['invalid'],r['model_calls'],r['extra_observations']))

    def test_skips_and_seed_groups(self):
        values=[dict(scene={'id':str(i),'seed':i//2},eligible=False,trajectories=[]) for i in range(4)]
        r=analyze(values,lambda _:None)
        self.assertEqual(2,r['seed_groups'])
        self.assertEqual(4,r['curves'][0]['skipped'])
        self.assertEqual(6,len(r['curves'][0]['paired']))
        self.assertEqual(set(METHODS),set(r['curves'][0]['methods']))

    def test_comparison_ignores_only_paths_not_state(self):
        a={'result_path':'old','result_sha256':'x','state':{'profile':'original'}}
        b=dict(a,result_path='new',result_sha256='y')
        self.assertEqual(semantic(a),semantic(b))
        b['state']={'profile':'changed'}
        self.assertNotEqual(semantic(a),semantic(b))


if __name__=='__main__':
    unittest.main()

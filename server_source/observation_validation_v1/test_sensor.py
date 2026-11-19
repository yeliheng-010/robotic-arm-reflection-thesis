"""观测独立性、预算、状态失效与真值隔离。"""
import copy
import json
import unittest
from unittest.mock import patch
import sensor
from policy import observe,decide
from pilot import scenes,extract_seeds,MAX_PHYSICAL
from loopstudy.actions import initial


def fixture(mechanism='occlusion'):
    step=dict(index=1,state=initial(),result_sha256='a'*64,feedback=dict(error_type='object_outside_container',
        evidence=dict(placement_residual_xy=[.1,-.1],motion_context={'phase':'unknown'})))
    return step,dict(seed=940001,source='RedBlock',mechanism=mechanism)


class SensorTests(unittest.TestCase):
    def test_replay_does_not_mutate_snapshot(self):
        step,item=fixture()
        before=copy.deepcopy(step)
        a=sensor.sample(step,item,number=1)
        self.assertEqual(a,sensor.sample(step,item,number=1))
        self.assertEqual(before,step)
        b=sensor.sample(step,item,number=2)
        self.assertNotEqual(a['seed_components'],b['seed_components'])
        self.assertEqual(a['source_sha256'],b['source_sha256'])

    def test_missing_measurement_consumes_bounded_extras(self):
        step,item=fixture()
        with patch.object(sensor,'OCCLUSION',1.):
            a=observe(step,item,mode='reobserve',used=0)
            b=observe(step,item,mode='reobserve',used=1)
            c=observe(step,item,mode='reobserve',used=2)
        self.assertEqual((2,1,0),(a['extra_cost'],b['extra_cost'],c['extra_cost']))
        self.assertNotIn('placement_residual_xy',a['feedback']['evidence'])

    def test_unrelated_missing_does_not_trigger_reobserve(self):
        step,item=fixture()
        step['feedback']['error_type']='collision'
        step['feedback']['evidence']['motion_context']['phase']='place_descent'
        with patch.object(sensor,'OCCLUSION',1.):
            value=observe(step,item,mode='reobserve',used=0)
        self.assertEqual(0,value['extra_cost'])
        self.assertIsNone(value['target_field'])

    def test_no_extra_baseline_never_spends_observation_budget(self):
        step,item=fixture()
        with patch.object(sensor,'OCCLUSION',1.):
            value=observe(step,item,mode='no_extra',used=0)
        self.assertEqual(0,value['extra_cost'])

    def test_latest_and_median_receive_identical_initial_measurements(self):
        step,item=fixture('outlier')
        a=observe(step,item,mode='latest',used=0)
        b=observe(step,item,mode='median',used=0)
        self.assertEqual(a['samples'],b['samples'])
        self.assertEqual((2,2),(a['extra_cost'],b['extra_cost']))
        self.assertEqual(0,observe(step,item,mode='median',used=2)['extra_cost'])

    def test_robust_aggregate_rejects_one_outlier(self):
        step,item=fixture('outlier')
        values=[sensor.sample(step,item,number=i) for i in range(3)]
        for s,r in zip(values,([.1,.2],[.101,.201],[.9,-.9])):
            s['feedback']['evidence']['placement_residual_xy']=r
        result=sensor.aggregate(values,mode='median')
        self.assertEqual([.101,.2],result['evidence']['placement_residual_xy'])

    def test_changed_state_or_snapshot_forbids_aggregation(self):
        step,item=fixture('outlier')
        values=[sensor.sample(step,item,number=i) for i in range(2)]
        values[1]['state']['profile']='descent_minus45'
        with self.assertRaises(AssertionError):
            sensor.aggregate(values,mode='median')

    def test_policy_has_no_truth_or_outlier_labels(self):
        step,item=fixture('outlier')
        observation=observe(step,item,mode='median',used=0)
        text=json.dumps(observation['feedback'])
        self.assertNotIn('"original"',text)
        self.assertNotIn('"outlier":',text)
        first=decide(step,observation)['selected']
        changed=copy.deepcopy(observation)
        for s in changed['samples']:
            s['audit']={'hidden':'forged'}
        self.assertEqual(first,decide(step,changed)['selected'])

    def test_design_counts_and_reserved_seed_extraction(self):
        rows=scenes()
        self.assertEqual(24,len(rows))
        self.assertEqual(144,sum(MAX_PHYSICAL[r['mechanism']] for r in rows))
        self.assertTrue(all(r['split']=='train_candidate' for r in rows))
        self.assertEqual({1,2,3},extract_seeds({'items':[{'seed':1}],'reserved_test_seeds':[2,3]}))


if __name__=='__main__':
    unittest.main()

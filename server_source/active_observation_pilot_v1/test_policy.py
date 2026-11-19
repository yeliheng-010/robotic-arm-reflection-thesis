"""用确定观测覆盖预算分配与隐私边界，不挑实际随机种子结果。"""
import copy
import unittest
from unittest.mock import patch
from ap_policy import observe,quality,decide
from ap_sensor import sample
from ap_common import scenes,SHARDS,SMOKE_SEEDS
from loopstudy.actions import initial


def fixture():
    step=dict(index=1,state=initial(),result_sha256='x'*64,feedback=dict(error_type='empty_grasp',
        evidence={'grasp_residual_xy':[.03,.02],'motion_context':{'phase':'grasp_pose'}}))
    return step,dict(seed=940201,source='RedBlock',factor_index=0)


def generated(values):
    def fake(step,item,*,number):
        value=copy.deepcopy(step['feedback'])
        value['evidence'].pop('grasp_residual_xy')
        if values[number] is not None:
            value['evidence']['grasp_residual_xy']=values[number]
        return dict(number=number,extra_cost=int(number>0),state=copy.deepcopy(step['state']),
            source_sha256=step['result_sha256'],feedback=value,audit={'hidden':'not policy input'})
    return fake


class PolicyTests(unittest.TestCase):
    def observe(self,method,values,used=0):
        step,item=fixture()
        with patch('ap_policy.sample',side_effect=generated(values)):
            return observe(step,item,method=method,used=used)

    def test_consistent_pair_saves_one_observation(self):
        values=[[.03,.02],[.031,.021],[.029,.02]]
        self.assertEqual(1,self.observe('adaptive',values)['extra_cost'])
        self.assertEqual(2,self.observe('fixed_first',values)['extra_cost'])

    def test_conflict_uses_last_budget(self):
        o=self.observe('adaptive',[[.03,.02],[.12,.1],[.031,.02]])
        self.assertEqual(2,o['extra_cost'])
        self.assertEqual('conflict',o['events'][1]['quality_before']['grasp_residual_xy']['status'])

    def test_missingness_reacquires_with_limit(self):
        o=self.observe('adaptive',[None,None,[.03,.02]])
        self.assertEqual((2,1),(o['extra_cost'],o['final_quality']['grasp_residual_xy']['visible_count']))
        self.assertEqual('unconfirmed',o['final_quality']['grasp_residual_xy']['status'])

    def test_all_missing_remains_missing(self):
        o=self.observe('adaptive',[None,None,None])
        self.assertEqual(2,o['extra_cost'])
        self.assertNotIn('grasp_residual_xy',o['feedback']['evidence'])

    def test_remaining_budget_can_be_used_later(self):
        self.assertEqual(1,self.observe('adaptive',[[.03,.02],[.031,.021],None],used=1)['extra_cost'])
        self.assertEqual(0,self.observe('adaptive',[[.03,.02],None,None],used=2)['extra_cost'])

    def test_no_cross_state_reuse(self):
        step,item=fixture()
        ss=[sample(step,item,number=i) for i in (0,1)]
        ss[1]['state']['profile']='changed'
        with self.assertRaises(AssertionError):
            quality(ss)

    def test_audit_poison_does_not_change_quality_or_action(self):
        step,item=fixture()
        o=observe(step,item,method='adaptive',used=0)
        poisoned=copy.deepcopy(o)
        for s in poisoned['samples']:
            s['audit']={'original':[999,999],'outlier':False}
        self.assertEqual(quality(o['samples']),quality(poisoned['samples']))
        self.assertEqual(decide(step,o)['selected'],decide(step,poisoned)['selected'])

    def test_sensor_reproducible_and_snapshot_immutable(self):
        step,item=fixture()
        original=copy.deepcopy(step)
        self.assertEqual(sample(step,item,number=1),sample(step,item,number=1))
        self.assertEqual(original,step)

    def test_majority_contamination_not_declared_true(self):
        o=self.observe('adaptive',[[.12,.1],[.121,.1],[.03,.02]])
        self.assertEqual(1,o['extra_cost'])
        self.assertEqual('consistent',o['final_quality']['grasp_residual_xy']['status'])
        self.assertGreater(o['feedback']['evidence']['grasp_residual_xy'][0],.1)

    def test_design_and_smoke_distribution(self):
        rows=scenes()
        self.assertEqual(24,len(rows))
        self.assertEqual(6,len({s['seed'] for s in rows}))
        smoke=[s for s in rows if s['seed'] in SMOKE_SEEDS]
        self.assertEqual(4,len(smoke))
        for shard in range(SHARDS):
            self.assertEqual(5,sum(s['seed'] not in SMOKE_SEEDS for s in rows[shard::SHARDS]))


if __name__=='__main__':
    unittest.main()

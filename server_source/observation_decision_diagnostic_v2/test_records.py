"""固定观测前缀、预算和任务覆盖；不使用未来结果选快照。"""
import copy
import json
import unittest
from unittest.mock import patch
from loopstudy.actions import initial
from od_records import observed,tasks,decode
from od_common import MAX_CALLS


class RecordTests(unittest.TestCase):
    def test_fixed_observation_prefix_and_true_budget(self):
        step=dict(index=2,state=initial(),result_sha256='x'*64,success=False,
            feedback=dict(error_type='object_outside_container',evidence={'placement_residual_xy':[.03,.02]}))
        source=dict(step=step,trace=dict(item=dict(seed=940301,source='RedBlock',factor_index=1)),
            decision=dict(choices=[{'context':{'remaining_observations':2}}],observation={'extra_cost':0}))
        frozen=copy.deepcopy(source)
        with patch('od_records.source_input',return_value=source):
            a,b,c=(observed({},n) for n in (0,1,2))
        self.assertEqual(a['samples'],b['samples'][:1])
        self.assertEqual(b['samples'],c['samples'][:2])
        self.assertEqual([2,1,0],[v['context']['remaining_observations'] for v in (a,b,c)])
        self.assertEqual(frozen,source)

    def test_inventory_cartesian_coverage_and_unique_ids(self):
        rows=[dict(id=f'{m}_{i}',method=m) for m in ('base_current','base_history') for i in range(41)]
        cases=[dict(case_id=f'c{i}',method='base_current') for i in range(11)]
        result=tasks(dict(rows=rows,cases=cases))
        self.assertEqual(MAX_CALLS,len(result))
        self.assertEqual(41,sum(t['kind']=='probe' for t in result))
        self.assertEqual(33,sum(t['kind']=='execute' for t in result))
        self.assertEqual(82,sum(t.get('variant')=='baseline' for t in result))

    def test_execute_cannot_sneak_observation_or_fallback(self):
        messages=[dict(role='system',content=''),dict(role='user',content='{"legal_action_ids":["a"]}')]
        with patch('od_records.check_response',return_value='{"action_id":"OBSERVE"}'):
            result=decode(dict(kind='execute'),messages,{})
        self.assertFalse(result['valid'])
        self.assertIsNone(result['action'])

    def test_wrong_cost_answer_counted_not_dropped(self):
        body=dict(legal_action_ids=['OBSERVE'],remaining_observations=2)
        text=json.dumps(dict(observe_legal=True,observation_cost=2,physical_cost=1,remaining_observations=2))
        messages=[dict(role='system',content=''),dict(role='user',content=json.dumps(body))]
        with patch('od_records.check_response',return_value=text):
            result=decode(dict(kind='probe'),messages,{})
        self.assertTrue(result['valid'])
        self.assertFalse(result['correct'])

    def test_incomplete_generation_preserved_as_invalid(self):
        with patch('od_records.check_response',side_effect=ValueError('Incomplete generation')):
            result=decode(dict(kind='execute'),[],{})
        self.assertFalse(result['valid'])
        self.assertIn('Incomplete',result['invalid'])


if __name__=='__main__':
    unittest.main()

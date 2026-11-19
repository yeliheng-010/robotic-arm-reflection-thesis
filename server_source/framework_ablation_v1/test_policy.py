"""检验真实候选生成、历史隔离、闭环次数和审计边界。"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import policy
from audit_task import decision_check
from common import in_phase
from loopstudy import episode,audit
from loopstudy.actions import initial,candidates


def fixture():
    return dict(index=1,state=initial(),feedback=dict(error_type='empty_grasp',
        evidence=dict(diagnostics=dict(available_candidate_count=5))))


class PolicyTests(unittest.TestCase):
    def test_retry_never_queries_feedback_candidates_or_model(self):
        step=fixture()
        with patch.object(policy,'rows_for',side_effect=AssertionError),patch.object(policy,'generate',side_effect=AssertionError):
            a=policy.decide(step,[],method='retry')
            b=policy.decide(dict(step,feedback={'hidden':'changed'}),[],method='retry')
        self.assertEqual(a['selected'],b['selected'])
        self.assertEqual(step['state'],a['selected']['state'])
        decision_check(a,[],method='retry')

    def test_candidates_really_ignore_previously_selected_state(self):
        step=fixture()
        rows=policy.rows_for(step['feedback'],step['state'])
        history=[dict(feedback=step['feedback'],before=step['state'],selected=rows[0])]
        old=candidates(step['feedback'],step['state'],history)
        self.assertNotIn(rows[0],old)
        with patch.object(policy,'generate',return_value={'text':json.dumps({'action_id':rows[0]['id']})}):
            for method in ('rule','current','history'):
                result=policy.decide(step,history,method=method)
                self.assertEqual(rows,result['candidates'])

    def test_current_prompt_invariant_to_history_and_full_differs_only_history(self):
        step=fixture()
        rows=policy.rows_for(step['feedback'],step['state'])
        d=dict(feedback=step['feedback'],before=step['state'],candidates=rows)
        history=[dict(feedback={'marker':'prior'},before=step['state'],selected=rows[0],secret_truth=42)]
        current=policy.prompt_for(d,history,method='current')
        self.assertEqual(current,policy.prompt_for(d,[],method='current'))
        full=policy.prompt_for(d,history,method='history')
        self.assertEqual(current[0],full[0])
        a,b=json.loads(current[1]['content']),json.loads(full[1]['content'])
        self.assertEqual([],a.pop('history'))
        self.assertEqual(1,len(b.pop('history')))
        self.assertEqual(a,b)
        self.assertNotIn('secret_truth',full[1]['content'])

    def test_both_model_policies_use_only_base(self):
        step=fixture()
        row=policy.rows_for(step['feedback'],step['state'])[0]
        with patch.object(policy,'generate',return_value={'text':json.dumps({'action_id':row['id']})}) as call:
            for method in ('current','history'):
                result=policy.decide(step,[],method=method)
                self.assertEqual(row,result['selected'])
        self.assertEqual(['base','base'],[c.args[0] for c in call.call_args_list])

    def test_illegal_model_reply_no_fallback(self):
        with patch.object(policy,'generate',return_value={'text':'{"action_id":"forged"}'}) as call:
            result=policy.decide(fixture(),[],method='history')
        self.assertIsNone(result['selected'])
        self.assertEqual(1,call.call_count)
        self.assertIn('invalid',result)

    def test_rule_tamper_rejected(self):
        result=policy.decide(fixture(),[],method='rule')
        decision_check(result,[],method='rule')
        forged=copy.deepcopy(result)
        forged['candidates']=[]
        with self.assertRaises(AssertionError):
            decision_check(forged,[],method='rule')

    def test_budget_and_patches_restored_after_exception(self):
        prior=(episode.MAX_ATTEMPTS,audit.MAX_ATTEMPTS,episode.decide,audit.decision_check)
        with self.assertRaises(RuntimeError):
            with policy.configured({'method':'retry','max_attempts':4},checker=lambda *a:None):
                self.assertEqual((4,4),(episode.MAX_ATTEMPTS,audit.MAX_ATTEMPTS))
                raise RuntimeError('probe')
        self.assertEqual(prior,(episode.MAX_ATTEMPTS,audit.MAX_ATTEMPTS,episode.decide,audit.decision_check))

    def test_actual_loop_respects_budgets_and_early_success(self):
        for budget,success_at,expected in ((3,99,3),(4,99,4),(4,2,2)):
            def attempt(item,state,*,directory,index):
                return dict(fixture(),index=index,state=state,success=index==success_at)
            with tempfile.TemporaryDirectory() as directory:
                with patch.object(episode,'attempt',attempt),patch.object(episode,'configuration',return_value={}):
                    with policy.configured({'method':'retry','max_attempts':budget}):
                        result=episode.run({},Path(directory)/'episode')
            self.assertEqual(expected,len(result['attempts']))
            self.assertEqual(expected-1,len(result['decisions']))

    def test_stage_budget_isolation(self):
        self.assertTrue(in_phase({'max_attempts':3},'batch3'))
        self.assertFalse(in_phase({'max_attempts':4},'batch3'))
        self.assertTrue(in_phase({'max_attempts':4},'batch4'))


if __name__=='__main__':
    unittest.main()

"""防止把首轮空历史、前缀重复和未观察成功误当成历史证据。"""
import copy
import json
import unittest
from core import compare_pair,features,aggregate,history_opportunities


def decision(history,*,choice='a',state=0):
    selected=dict(id=choice,kind='measured_grasp',state=state+1)
    prompt=dict(error={'error_type':'empty_grasp'},state=state,candidates=[selected],history=history)
    event=dict(request={'messages':[{'role':'system','content':'choose'},
        {'role':'user','content':json.dumps(prompt)}]},text=json.dumps({'action_id':choice}))
    return dict(event=event,selected=selected)


class CoreTests(unittest.TestCase):
    def test_first_position_not_counted_as_history_exposed(self):
        a=dict(decisions=[decision([]),decision([],state=1)])
        b=dict(decisions=[decision([]),decision([{'past':1}],state=1)])
        result=compare_pair(a,b)['counts']
        self.assertEqual(2,result['paired_positions'])
        self.assertEqual(1,result['nonempty_history_positions'])
        self.assertEqual(2,result['same_input_same_choice'])

    def test_changed_selection_with_same_input_detected(self):
        a=decision([])
        b=copy.deepcopy(a)
        b['selected']['id']='b'
        result=compare_pair({'decisions':[a]},{'decisions':[b]})
        self.assertEqual(1,result['counts']['same_input_different_choice'])
        self.assertEqual(1,len(result['differences']))

    def test_different_current_states_not_same_input_comparison(self):
        result=compare_pair({'decisions':[decision([])]},{'decisions':[decision([],state=2)]})
        self.assertEqual(1,result['counts']['different_current_input'])
        self.assertEqual(0,result['counts'].get('same_input_different_choice',0))

    def test_current_history_leak_rejected(self):
        with self.assertRaises(AssertionError):
            compare_pair({'decisions':[decision([1])]},{'decisions':[decision([])]})

    def test_alias_groups_require_different_history(self):
        same=decision([])
        varied=decision([{'previous':'failure'}])
        a=history_opportunities([('a',same),('b',same)])
        b=history_opportunities([('a',same),('b',varied)])
        self.assertEqual([],a['same_current_different_history_groups'])
        self.assertEqual(1,len(b['same_current_different_history_groups']))

    def test_features_distinguish_prior_measurement_and_candidate(self):
        candidate=dict(id='a',kind='exploratory_depth',state=0)
        previous=dict(feedback={'evidence':{'grasp_residual_xy':[.1,.2]}})
        current=dict(before=1,feedback={'error_type':'empty_grasp','evidence':{}},
                     candidates=[candidate],selected=candidate)
        result=dict(decisions=[previous,current],attempts=[dict(state=0,success=False),
            dict(state=1,success=False,noise_audit={'grasp_residual_xy':{'missing':True}}),
            dict(state=0,success=False)])
        row=features(result,1,initial_state=0,rule_choice=candidate)
        self.assertEqual(['grasp_residual_xy'],row['historical_visible_fields'])
        self.assertEqual(1,row['past_failed_states_available'])
        self.assertTrue(row['selected_past_failed_state'])
        self.assertFalse(row['next_attempt_success'])
        self.assertEqual(0,aggregate([row])['measured_option'])


if __name__=='__main__':
    unittest.main()

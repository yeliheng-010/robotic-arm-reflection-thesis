"""验证已发现的阶段标签遗漏与配对统计边界。"""
import unittest
from copy import deepcopy
from oa_metrics import consumed_field,field_metrics,paired_budgets,condition,initial_pair


def decision(values,*,effective):
    field='grasp_residual_xy'
    samples=[dict(number=i,source_sha256='same',state={},
        feedback={'evidence':{field:v}},audit={field:{'original':[0.,0.],'outlier':i==2}})
        for i,v in enumerate(values)]
    return dict(feedback={'evidence':{field:effective}},
        selected={'kind':'measured_grasp','facts':{'measurement':effective}},
        observation={'samples':samples,'target_field':None})


class AnalysisTests(unittest.TestCase):
    def test_consumed_field_without_heuristic_target(self):
        d=decision([[0,0]],effective=[0,0])
        self.assertEqual('grasp_residual_xy',consumed_field(d))

    def test_measurement_must_match_action_facts(self):
        d=decision([[0,0]],effective=[0,0])
        d['selected']['facts']['measurement']=[1,1]
        with self.assertRaises(AssertionError):
            consumed_field(d)

    def test_nonmeasurement_action_is_not_assigned_field(self):
        self.assertIsNone(consumed_field({'selected':{'kind':'exploratory_slow'}}))

    def test_higher_median_error_is_retained(self):
        values=[[.02,0],[.03,0],[.001,0]]
        a=decision(values,effective=values[-1])
        b=decision(values,effective=values[0])
        self.assertEqual('higher',field_metrics(a,b,field='grasp_residual_xy')['error_direction'])

    def test_cross_state_sample_rejected(self):
        a=decision([[0,0],[0,0]],effective=[0,0])
        a['observation']['samples'][1]['state']={'changed':True}
        with self.assertRaises(AssertionError):
            field_metrics(a,deepcopy(a),field='grasp_residual_xy')

    def test_both_pair_directions_retained(self):
        traces={'latest':{'attempts':[{'success':False},{'success':True}]},
                'median':{'attempts':[{'success':False},{'success':False},{'success':True}]}}
        self.assertEqual('latest_only',paired_budgets(traces)[1]['paired'])
        self.assertEqual('median_only',paired_budgets(dict(latest=traces['median'],median=traces['latest']))[1]['paired'])

    def test_skipped_has_no_observed_failure(self):
        value={'scene':{'id':'skip','seed':1},'eligible':False,'trajectories':[]}
        self.assertEqual([],condition(value,lambda _:None)['budgets'])

    def test_initial_success_has_no_measurement_comparison(self):
        trace={'attempts':[{'success':True}],'decisions':[]}
        self.assertIsNone(initial_pair({'latest':trace,'median':deepcopy(trace)}))


if __name__=='__main__':
    unittest.main()

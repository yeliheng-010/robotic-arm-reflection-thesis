"""验证因素隔离、固定策略与统计边界。"""
import copy
import unittest
from recovery.design import runs,configuration,sequence_changes
from recovery.feedback import project
from recovery.methods import choose_stage
from recovery.audit import counts
from reflection.reflector import Parameters


class StudyTests(unittest.TestCase):
    def test_manifest_complete_and_unselected_seeds_excluded(self):
        items = runs()
        self.assertEqual(35,len(items))
        self.assertEqual(35,len({r['id'] for r in items}))
        self.assertEqual(15,sum(r['study']=='feedback' for r in items))
        self.assertEqual({905001},{r['seed'] for r in items if r['study']=='collision'})

    def test_feedback_only_changes_feedback(self):
        configs = [configuration(next(r for r in runs() if r['study']=='feedback' and r['mode']==m))
                   for m in ('noisy','ideal','missing_xy')]
        physical = [{k:v for k,v in c.items() if k!='feedback'} for c in configs]
        self.assertEqual(physical[0],physical[1])
        self.assertEqual(physical[0],physical[2])

    def test_missing_only_xy_preserves_contacts(self):
        config = configuration(next(r for r in runs() if r['study']=='feedback' and r['mode']=='missing_xy'))
        report = dict(error_type='object_dropped',stage='execution',evidence={
            'grasp_residual_xy':[.01,.02],'placement_residual_xy':[.02,.03],
            'held':['target'],'contacts':[['finger','target']],'diagnostics':{'motion_segment':'lift'}})
        before = copy.deepcopy(report)
        value = project(report,config,attempt=1)['evidence']
        self.assertNotIn('grasp_residual_xy',value)
        self.assertNotIn('placement_residual_xy',value)
        self.assertEqual([['finger','target']],value['contacts'])
        self.assertEqual(['target'],value['held'])
        self.assertEqual(before,report)

    def test_sequences_reach_same_end_in_distinct_orders(self):
        endings,firsts = [],[]
        for mode in ('candidate_depth','depth_candidate'):
            p = Parameters()
            first = sequence_changes(mode,p,step=0)
            firsts.append(first)
            p = p.updated(first)
            p = p.updated(sequence_changes(mode,p,step=1))
            endings.append(p)
        self.assertNotEqual(firsts[0],firsts[1])
        self.assertEqual(endings[0],endings[1])
        self.assertEqual(1,endings[0].candidate_index)
        self.assertEqual(-.01,endings[0].grasp_offset[2])

    def test_stage_rule_uses_lift_only_for_relevant_collision(self):
        rows = [dict(id='lift',kind='exploratory_lift',changes={'lift_height':.45}),
                dict(id='measured',kind='measured_grasp',changes={'grasp_offset':[.01,0,0]})]
        report = dict(error_type='collision',evidence={'diagnostics':{'motion_segment':'transport'}})
        self.assertEqual('lift',choose_stage(rows,Parameters(),report=report)['id'])
        report['evidence']['diagnostics']['motion_segment'] = 'descent'
        self.assertEqual('measured',choose_stage(rows,Parameters(),report=report)['id'])

    def test_service_error_is_not_double_counted(self):
        result = {'records':[{'reflection_error':'http'},{'reflection_error':'invalid'}]}
        value = counts(result,[{'service_error':True,'elapsed_s':2},{'elapsed_s':3}])
        self.assertEqual(1,value['service_errors'])
        self.assertEqual(1,value['invalid'])
        self.assertEqual(5,value['model_latency_s'])


if __name__=='__main__':
    unittest.main()

"""测试配对随机数、投影隔离和全分母。"""
from copy import deepcopy
import unittest
from noisyloop.feedback import seed_for,project_step
from noisyloop.design import items,is_smoke
from loopstudy.actions import initial
from loopstudy.selection import messages


class NoiseLoopTests(unittest.TestCase):
    def setUp(self):
        self.item=dict(seed=905001,factor='position_only',noise_repeat=0,arm='new_rule',
                       noise_profile=dict(sigma_m=.005,missing_probability=0.))
        self.step=dict(index=1,feedback={'error_type':'collision','evidence':{'grasp_residual_xy':[.1,-.1]}})

    def test_methods_have_identical_noise(self):
        other=dict(self.item,arm='hybrid')
        self.assertEqual(project_step(self.step,self.item),project_step(self.step,other))

    def test_repeats_and_attempts_have_distinct_seeds(self):
        values={seed_for(dict(self.item,noise_repeat=r),i) for r in (0,1) for i in (1,2,3)}
        self.assertEqual(6,len(values))

    def test_profile_amplitude_does_not_change_random_seed(self):
        other=dict(self.item,noise_profile=dict(sigma_m=.015,missing_probability=.25))
        self.assertEqual(seed_for(self.item,1),seed_for(other,1))

    def test_original_values_stay_out_of_model_payload(self):
        before=deepcopy(self.step)
        shown=project_step(self.step,self.item)
        self.assertEqual(before,self.step)
        payload=messages(shown['feedback'],initial(),rows=[],history=[])
        text=payload[1]['content']
        self.assertNotIn('noise_audit',text)
        self.assertNotIn('projection_seed',text)
        self.assertNotIn('"original": [',text)

    def test_zero_distortion_preserves_measurement(self):
        item=dict(self.item,noise_profile=dict(sigma_m=0.,missing_probability=0.))
        value=project_step(self.step,item)
        self.assertEqual(self.step['feedback']['evidence']['grasp_residual_xy'],
                         value['feedback']['evidence']['grasp_residual_xy'])

    def test_unique_tasks_and_balanced_pairs(self):
        rows=items()
        self.assertEqual(144,len(rows))
        self.assertEqual(144,len({r['id'] for r in rows}))
        self.assertEqual(72,len({r['pair_id'] for r in rows}))
        self.assertEqual(12,sum(is_smoke(r) for r in rows))
        for pair in {r['pair_id'] for r in rows}:
            self.assertEqual({'new_rule','hybrid'},{r['arm'] for r in rows if r['pair_id']==pair})


if __name__=='__main__':
    unittest.main()

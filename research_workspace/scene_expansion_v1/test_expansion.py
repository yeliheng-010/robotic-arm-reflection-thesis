"""场景、划分、噪声和资格判定的行为测试。"""
from copy import deepcopy
import unittest
import numpy as np
from expand.design import scenes,items,configuration,is_smoke,RESERVED_TEST_SEEDS
from expand.feedback import project_step
from expand.qualify import classify
from expand.bridge import bound
from loopstudy import episode,audit
from diversity.config import SLOTS


class ExpansionTests(unittest.TestCase):
    def test_denominators(self):
        self.assertEqual(100,len(scenes()))
        self.assertEqual(200,len({r['id'] for r in items()}))
        self.assertEqual(6,sum(is_smoke(s) for s in scenes()))
        self.assertEqual(12,sum(is_smoke(s) for s in items()))

    def test_split_by_seed(self):
        train={r['seed'] for r in scenes() if r['split']=='train_candidate'}
        validation={r['seed'] for r in scenes() if r['split']=='development_validation'}
        self.assertFalse(train & validation)
        self.assertFalse((train|validation) & set(RESERVED_TEST_SEEDS))
        self.assertEqual((8,2),(len(train),len(validation)))

    def test_pair_inputs(self):
        rows=items()
        for first,second in zip(rows[::2],rows[1::2]):
            self.assertEqual(configuration(first),configuration(second))
            step=dict(index=1,feedback={'evidence':{'grasp_residual_xy':[.01,-.02]}})
            self.assertEqual(project_step(step,first),project_step(step,second))

    def test_factors_do_not_leak(self):
        for item in scenes():
            config=configuration(item)
            self.assertEqual(0,config['profile']['depth_sigma_m'])
            self.assertEqual(0,config['profile']['dropout'])
            for body in config['bodies'].values():
                self.assertLessEqual(abs(body['yaw_delta']),np.radians(config['profile']['yaw_degrees']))
                self.assertEqual(1,body['density_scale'])
                self.assertEqual(1,body['friction_scale'])
            if item['factor']!='container_1cm':
                self.assertTrue(all(xy==[0.,0.] for xy in config['containers'].values()))

    def test_noise_does_not_mutate_or_change_class(self):
        step=dict(index=1,feedback={'error_type':'collision','evidence':{'grasp_residual_xy':[.1,-.1]}})
        saved=deepcopy(step)
        actual=project_step(step,items()[0])
        self.assertEqual(saved,step)
        self.assertEqual('collision',actual['feedback']['error_type'])

    def test_qualification_is_not_model_dependent(self):
        self.assertEqual('challenge',classify(True,True,success=False,contact=True))
        self.assertEqual('easy_control',classify(True,True,success=True,contact=False))
        self.assertEqual('control_failed',classify(True,False,success=False,contact=True))
        self.assertEqual('geometry_ineligible',classify(False,True,success=False,contact=True))
        self.assertEqual('non_target_failure',classify(True,True,success=False,contact=False))

    def test_configuration_binding_restores_after_failure(self):
        original=(episode.configuration,audit.configuration,episode.collision_context)
        with self.assertRaises(RuntimeError):
            with bound(items()[0],enabled=False):
                self.assertIs(configuration,episode.configuration)
                self.assertIs(configuration,audit.configuration)
                raise RuntimeError('deliberate cleanup check')
        self.assertEqual(original,(episode.configuration,audit.configuration,episode.collision_context))

    def test_layout_and_container_bounds(self):
        for item in scenes():
            value=configuration(item)
            for body,slot in zip(value['bodies'].values(),SLOTS):
                self.assertLessEqual(float(np.max(np.abs(np.array(body['xy'])-slot))),value['profile']['xy_m']+1e-12)
            for offset in value['containers'].values():
                self.assertLessEqual(max(abs(x) for x in offset),value['profile']['container_xy_m'])


if __name__=='__main__':
    unittest.main()

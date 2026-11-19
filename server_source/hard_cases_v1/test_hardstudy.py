"""干预组合、方法配对、作用持续性与真值隔离。"""
from copy import deepcopy
import unittest
import numpy as np
from diversity.scene import ScenarioFault
from reflection.fault_injection import Fault
from loopstudy.actions import initial
from loopstudy.selection import messages
from hardstudy.design import scenes,items,configuration,is_smoke,RESERVED_TEST_SEEDS
from hardstudy.intervention import capture,expected
from hardstudy.feedback import project_step
from hardstudy.qualify import classify


class HardStudyTests(unittest.TestCase):
    def test_matrix(self):
        self.assertEqual(200,len(scenes()))
        self.assertEqual(400,len({r['id'] for r in items()}))
        self.assertEqual(10,sum(is_smoke(r) for r in scenes()))
        self.assertEqual(20,sum(is_smoke(r) for r in items()))

    def test_split(self):
        train={r['seed'] for r in scenes() if r['split']=='train_candidate'}
        validation={r['seed'] for r in scenes() if r['split']=='development_validation'}
        self.assertEqual((16,4),(len(train),len(validation)))
        self.assertFalse(train & validation)
        self.assertFalse((train|validation) & set(RESERVED_TEST_SEEDS))

    def test_compounds_share_single_factor_values(self):
        rows={r['factor']:r for r in scenes() if r['seed']==920001 and r['source']=='RedBlock'}
        self.assertEqual(rows['grasp_bias']['injection']['grasp'],rows['grasp_place']['injection']['grasp'])
        self.assertEqual(rows['place_bias']['injection']['place'],rows['grasp_place']['injection']['place'])
        self.assertEqual(rows['grasp_bias']['injection']['grasp'],rows['grasp_collision']['injection']['grasp'])
        self.assertTrue(rows['grasp_collision']['injection']['collision'])
        configs=[configuration(r) for r in rows.values()]
        self.assertTrue(all(c==configs[0] for c in configs))

    def test_magnitude_and_paired_noise(self):
        for row in scenes():
            for name,low,high in (('grasp',.025,.065),('place',.10,.18)):
                norm=np.linalg.norm(row['injection'][name])
                self.assertTrue(norm==0 or low<=norm<=high)
        rows=items()
        step=dict(index=1,feedback={'evidence':{'grasp_residual_xy':[.02,-.03]}})
        for first,second in zip(rows[::2],rows[1::2]):
            self.assertEqual(project_step(step,first),project_step(step,second))

    def test_persistent_bias_and_control(self):
        row=next(r for r in scenes() if r['factor']=='grasp_place')
        fault=ScenarioFault(Fault('none'),configuration(row))
        for _ in range(3):
            with capture(row) as trace:
                self.assertEqual(row['injection']['grasp'],fault.grasp_bias())
                self.assertEqual(row['injection']['place'],fault.place_bias())
                self.assertEqual(1,len(trace['grasp']))
        with capture(row,enabled=False):
            self.assertEqual([0.,0.,0.],fault.grasp_bias())
            self.assertEqual([0.,0.,0.],fault.place_bias())
        self.assertFalse(expected(row,False)['collision'])

    def test_capture_restores_on_error(self):
        original=(ScenarioFault.grasp_bias,ScenarioFault.place_bias)
        with self.assertRaises(RuntimeError):
            with capture(scenes()[0]):
                raise RuntimeError('cleanup test')
        self.assertEqual(original,(ScenarioFault.grasp_bias,ScenarioFault.place_bias))

    def test_truth_not_in_visible_request(self):
        step=dict(index=1,feedback={'error_type':'empty_grasp','evidence':{'grasp_residual_xy':[.01,.02]}})
        before=deepcopy(step)
        shown=project_step(step,items()[0])
        payload=messages(shown['feedback'],initial(),rows=[],history=[])
        text=str(payload)
        for key in ('injection','intervention','noise_audit','specification','projection_seed'):
            self.assertNotIn(key,text)
        self.assertEqual(before,step)

    def test_qualification_preserves_real_outcomes(self):
        self.assertEqual('challenge',classify(True,True,success=False))
        self.assertEqual('easy_control',classify(True,True,success=True))
        self.assertEqual('control_failed',classify(True,False,success=False))
        self.assertEqual('geometry_ineligible',classify(False,False,success=False))


if __name__=='__main__':
    unittest.main()

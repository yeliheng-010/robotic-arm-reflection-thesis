"""缺失干预只改变可见性，预算设置仅限进程内临时绑定。"""
import importlib.util
import unittest
from hardstudy.feedback import project_step
from loopstudy import episode, audit


class VariantTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('variant'))
        import variant
        return variant

    def fixture(self):
        item=dict(seed=920018,factor_index=4,noise_profile=dict(sigma_m=.005,missing_probability=.25))
        step=dict(index=1,feedback=dict(error_type='object_dropped',evidence=dict(grasp_residual_xy=[.05,.02])))
        return item,step

    def test_no_missing_preserves_seed_delta_and_noise(self):
        module=self.module()
        item,step=self.fixture()
        old=project_step(step,item)
        self.assertTrue(old['noise_audit']['grasp_residual_xy']['missing'])
        actual=module.project_variant(step,item,variant='no_missing')
        self.assertEqual(old['projection_seed'],actual['projection_seed'])
        first,last=old['noise_audit']['grasp_residual_xy'],actual['noise_audit']['grasp_residual_xy']
        self.assertEqual(first['delta'],last['delta'])
        self.assertEqual(first['original'],last['original'])
        self.assertFalse(last['missing'])
        expected=[a+b for a,b in zip(first['original'],first['delta'])]
        self.assertEqual(expected,actual['feedback']['evidence']['grasp_residual_xy'])
        self.assertNotEqual(first['original'],expected)
        self.assertEqual(.25,item['noise_profile']['missing_probability'])

    def test_budget_variant_preserves_projection(self):
        module=self.module()
        item,step=self.fixture()
        self.assertEqual(project_step(step,item),module.project_variant(step,item,variant='budget4'))

    def test_budget_binding_restores_on_exception(self):
        module=self.module()
        original=(episode.MAX_ATTEMPTS,audit.MAX_ATTEMPTS)
        with self.assertRaisesRegex(RuntimeError,'probe'):
            with module.configured(dict(variant='budget4',max_attempts=4)):
                self.assertEqual((4,4),(episode.MAX_ATTEMPTS,audit.MAX_ATTEMPTS))
                raise RuntimeError('probe')
        self.assertEqual(original,(episode.MAX_ATTEMPTS,audit.MAX_ATTEMPTS))

    def test_variant_budget_mismatch_rejected(self):
        module=self.module()
        with self.assertRaises(AssertionError):
            with module.configured(dict(variant='no_missing',max_attempts=4)):
                self.fail('Combined intervention must be rejected')


if __name__=='__main__':
    unittest.main()

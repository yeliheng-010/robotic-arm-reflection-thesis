"""噪声界限、来源隔离与缺失语义。"""
from copy import deepcopy
import unittest
from projection import project,FIELDS


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.raw=dict(error_type='collision',evidence={FIELDS[0]:[.01,-.02],FIELDS[1]:[.02,.03],
            'motion_context':{'phase':'place_descent'},'contact_details':{'body':'wrist_1_link'}})

    def test_zero_noise_preserves_values_and_input(self):
        before=deepcopy(self.raw)
        value,_=project(self.raw,dict(sigma_m=0.,missing_probability=0.),seed=1)
        self.assertEqual(before,self.raw)
        for field in FIELDS:
            self.assertEqual(self.raw['evidence'][field],value['evidence'][field])

    def test_seed_is_reproducible_and_noise_bounded(self):
        profile=dict(sigma_m=.005,missing_probability=0.)
        first=project(self.raw,profile,seed=42)
        self.assertEqual(first,project(self.raw,profile,seed=42))
        self.assertTrue(all(abs(d)<=.015 for r in first[1].values() for d in r['delta']))
        self.assertEqual(self.raw['evidence']['contact_details'],first[0]['evidence']['contact_details'])
        self.assertNotIn('original',first[0]['evidence']['residual_corruption'])

    def test_missing_is_absent_not_zero(self):
        seen=False
        for seed in range(20):
            value,audit=project(self.raw,dict(sigma_m=0.,missing_probability=.25),seed=seed)
            for field,entry in audit.items():
                if entry['missing']:
                    seen=True
                    self.assertNotIn(field,value['evidence'])
        self.assertTrue(seen)


if __name__=='__main__':
    unittest.main()

import unittest
from visibility_calibration_v1.policy import gate_at,select_pairs


def report(fraction=.7,extra=()):
    return dict(gate=dict(objects={'source':dict(visible_fraction=fraction,
        reasons=['visible_fraction',*extra]),'background':dict(visible_fraction=.9,reasons=[])}))


class PolicyTests(unittest.TestCase):
    def test_only_fraction_requirement_changes(self):
        self.assertTrue(gate_at(report(),.6))
        self.assertFalse(gate_at(report(),.8))
        self.assertFalse(gate_at(report(extra=['pixels']),.6))
        self.assertFalse(gate_at(report(extra=['connected']),.6))

    def test_missing_and_invalid_measurements_reject(self):
        self.assertFalse(gate_at({},.1))
        self.assertFalse(gate_at(report(float('nan')),.1))
        self.assertFalse(gate_at(report(),.5,names=['missing']))
        self.assertFalse(gate_at(dict(gate=dict(objects={})),.5))

    def test_target_diagnostic_does_not_claim_full_frame_pass(self):
        value=report()
        value['gate']['objects']['background']['reasons']=['pixels']
        self.assertTrue(gate_at(value,.6,names=['source']))
        self.assertFalse(gate_at(value,.6))

    def test_pairs_reject_identical_views_and_sparse_targets(self):
        cameras=[dict(position=x,target=[0,0,0]) for x in ([1,0,0],[0,1,0],[1,0,0])]
        rows=[dict(index=i,camera=c,source_pixels=200,source_fraction=.5) for i,c in enumerate(cameras)]
        self.assertEqual([(0,1),(1,2)],select_pairs(rows))
        rows[1]['source_pixels']=0
        self.assertEqual([],select_pairs(rows))

    def test_pair_budget_and_determinism(self):
        import math
        rows=[dict(index=i,camera=dict(position=[math.cos(i),math.sin(i),1],target=[0,0,0]),
                   source_pixels=200,source_fraction=(i%8+1)/10) for i in range(25)]
        pairs=select_pairs(rows)
        self.assertEqual(24,len(pairs))
        self.assertEqual(pairs,select_pairs(rows))
        self.assertEqual(len(pairs),len(set(pairs)))

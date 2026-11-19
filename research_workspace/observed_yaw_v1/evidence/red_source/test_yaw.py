import unittest
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from cp_candidates import candidates as original
from yc_candidates import candidates


class YawTests(unittest.TestCase):
    def setUp(self):
        self.pose=sm.SE3(1.,.5,.8)
        self.fit=dict(available=True,center=[1.,.5,.77],closing_axis=[1.,0.,0.],
                      top_z_m=.8,length_m=.13,width_m=.033)

    def test_preserves_originals_then_expands_orientation(self):
        old=original(self.pose,self.fit)
        rows=candidates(self.pose,self.fit)
        self.assertGreater(len(rows),len(old))
        self.assertLessEqual(len(rows),90)
        for expected,actual in zip(old,rows):
            self.assertEqual(expected['id'],actual['id'])
            np.testing.assert_array_equal(expected['pose'].A,actual['pose'].A)

    def test_vertical_axis_and_center_unchanged(self):
        old=original(self.pose,self.fit)
        rows=candidates(self.pose,self.fit)
        self.assertGreater(len(rows),len(old))
        centers={tuple(r['pose'].t) for r in old}
        for row in rows:
            np.testing.assert_allclose([0.,0.,-1.],row['pose'].R[:,0],atol=1e-12)
            self.assertIn(tuple(row['pose'].t),centers)
            self.assertLessEqual(np.linalg.norm(row['pose'].t-self.pose.t),.050+1e-12)
        unique={tuple(np.round(r['pose'].A.flatten(),12)) for r in rows}
        self.assertEqual(len(rows),len(unique))

    def test_missing_or_distant_observation_rejected(self):
        self.assertEqual([],candidates(self.pose,dict(available=False)))
        self.assertEqual([],candidates(sm.SE3(10.,10.,10.),self.fit))


if __name__ == '__main__':
    unittest.main(verbosity=2)

import unittest
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from yc_candidates import candidates as original
from lc_candidates import candidates


class LongTests(unittest.TestCase):
    def setUp(self):
        self.pose=sm.SE3(1.,.5,.8)
        self.fit=dict(available=True,center=[1.,.5,.77],closing_axis=[1.,0.,0.],
                      top_z_m=.8,length_m=.13,width_m=.033)

    def test_preserves_existing_and_adds_bounded_shifts(self):
        old=original(self.pose,self.fit)
        rows=candidates(self.pose,self.fit)
        self.assertGreater(len(rows),len(old))
        self.assertLessEqual(len(rows),180)
        self.assertTrue(any(abs(r['pose'].t[1]-.5)>.02 for r in rows))
        for expected,actual in zip(old,rows):
            self.assertEqual(expected['id'],actual['id'])
            np.testing.assert_array_equal(expected['pose'].A,actual['pose'].A)
        for row in rows:
            self.assertLessEqual(abs(row['pose'].t[1]-.5),.035+1e-12)
            self.assertLessEqual(np.linalg.norm(row['pose'].t-self.pose.t),.050+1e-12)
        self.assertEqual(len(rows),len({tuple(np.round(r['pose'].A.flatten(),12)) for r in rows}))

    def test_compact_objects_not_expanded(self):
        fitted=dict(self.fit,length_m=.06)
        old=original(self.pose,fitted)
        new=candidates(self.pose,fitted)
        self.assertEqual([x['id'] for x in old],[x['id'] for x in new])

    def test_unavailable_observation_rejected(self):
        self.assertEqual([],candidates(self.pose,dict(available=False)))


if __name__ == '__main__':
    unittest.main(verbosity=2)

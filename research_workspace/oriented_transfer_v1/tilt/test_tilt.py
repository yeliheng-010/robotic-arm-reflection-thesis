import unittest
from itertools import islice,product
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from tt_candidates import candidates
from ot_geometry import release_target,moved


class TiltTests(unittest.TestCase):
    def setUp(self):
        self.points=np.array(list(product((-.08,.08),(-.02,.02),(-.01,.01))))
        self.dim=dict(bin_center=[1.,2.,0.],interior_half=[.15,.12],wall_top=.3)
        self.grasps=[dict(id='a|1,1,-1',pose='a',config=[1,1,-1]),
                     dict(id='b|1,1,-1',pose='b',config=[1,1,-1]),
                     dict(id='c|1,1,-1',pose='c',config=[1,1,-1])]
        self.poses={x:sm.SE3() for x in 'abc'}

    def test_independent_release_branches_and_both_tilt_signs(self):
        rows=list(islice(candidates(self.grasps,self.poses,points=self.points,dimensions=self.dim),640))
        self.assertEqual(640,len(rows))
        self.assertEqual({-30.,-15.,0.,15.,30.},{r['pitch'] for r in rows})
        self.assertEqual(8,len({tuple(r['config']) for r in rows}))
        self.assertEqual({'a','b'},{r['grasp']['pose'] for r in rows})
        self.assertTrue(all(r['grasp']['config']==[1,1,-1] for r in rows))

    def test_tilt_changes_height_and_preserves_grasp_offset(self):
        grasp=sm.SE3(.03,0.,0.)
        pose=release_target(grasp,sm.SO3.Ry(np.pi/6).R,points=self.points,
            dimensions=self.dim,grid=[0,0],gap=.04)
        np.testing.assert_allclose([1.025980762113533,2.,.3736602540378444],pose.t,atol=1e-12,rtol=0)
        result=moved(self.points,grasp,pose)
        self.assertAlmostEqual(.34,float(result[:,2].min()),places=12)

    def test_no_safe_grasp_yields_no_release(self):
        self.assertEqual([],list(candidates([],{},points=self.points,dimensions=self.dim)))


if __name__=='__main__':
    unittest.main(verbosity=2)

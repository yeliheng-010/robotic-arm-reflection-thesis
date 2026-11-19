"""捕获漏旋转、抓点偏心和中途体积碰撞。"""
import unittest
import numpy as np
import spatialmath as sm
from itertools import product
from ot_geometry import moved,release_target


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.points=np.array(list(product((-.08,.08),(-.02,.02),(-.01,.01))))
        self.dim=dict(bin_center=[1.,2.,0.],interior_half=[.15,.12],wall_top=.3)

    def test_offcenter_grasp_rotates_object_about_tcp(self):
        grasp=sm.SE3(.1,0.,0.)
        release=sm.SE3.Rt(sm.SO3.Rz(np.pi/2),[1.,2.,3.])
        actual=moved(np.array([[0.,0.,0.],[.2,0.,0.]]),grasp,release)
        np.testing.assert_allclose([[1.,1.9,3.],[1.,2.1,3.]],actual,atol=1e-12,rtol=0)

    def test_rotated_fit_and_offset(self):
        grasp=sm.SE3(.03,0.,0.)
        pose=release_target(grasp,sm.SO3.Rz(np.pi/2).R,points=self.points,
            dimensions=self.dim,grid=[1,1],gap=.04)
        # 旋转后半长宽为.02/.08，保留.02余量；TCP比盒中心高y=.03。
        np.testing.assert_allclose([1.11,2.05,.35],pose.t,atol=1e-12,rtol=0)

    def test_rejects_unfit_rotated_volume(self):
        with self.assertRaises(ValueError):
            release_target(sm.SE3(),np.eye(3),points=self.points,
                dimensions=dict(self.dim,interior_half=[.09,.12]),grid=[0,0],gap=.01)

    def test_identity_keeps_points(self):
        pose=sm.SE3(.4,.2,.1)
        np.testing.assert_allclose(self.points,moved(self.points,pose,pose),atol=1e-12,rtol=0)

    def test_invalid_points_are_rejected(self):
        with self.assertRaises(ValueError):
            moved(np.array([[float('nan'),0.,0.]]),sm.SE3(),sm.SE3())


if __name__=='__main__':
    unittest.main(verbosity=2)

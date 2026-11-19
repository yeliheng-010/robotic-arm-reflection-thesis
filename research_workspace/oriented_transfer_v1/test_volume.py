"""真实MuJoCo合成夹具检查旋转过程与状态隔离。"""
import unittest
import numpy as np
import mujoco
import spatialmath as sm
from ot_volume import body_pose,place,collisions,corners

XML='<mujoco><worldbody><geom name="obstacle" type="sphere" size=".01" pos=".05 .05 .2"/><body name="held" pos="0 0 .2"><freejoint/><geom type="box" size=".08 .01 .01" mass="1"/></body></worldbody></mujoco>'


class VolumeTests(unittest.TestCase):
    def setUp(self):
        self.model=mujoco.MjModel.from_xml_string(XML)
        self.original=mujoco.MjData(self.model)
        mujoco.mj_forward(self.model,self.original)
        self.copy=mujoco.MjData(self.model)
        self.copy.qpos[:]=self.original.qpos
        mujoco.mj_forward(self.model,self.copy)
        self.pose=body_pose(self.model,self.original,'held')

    def test_collision_only_between_safe_endpoints(self):
        hits=[]
        for angle in (0.,np.pi/4,np.pi/2):
            release=sm.SE3.Rt(sm.SO3.Rz(angle),[0.,0.,.2])
            place(self.model,self.copy,source='held',initial=self.pose,grasp=self.pose,release=release)
            hits.append(bool(collisions(self.model,self.copy,'held')))
        self.assertEqual([False,True,False],hits)

    def test_local_corners_track_orientation(self):
        release=sm.SE3.Rt(sm.SO3.Rz(np.pi/2),[0.,0.,.2])
        place(self.model,self.copy,source='held',initial=self.pose,grasp=self.pose,release=release)
        points=corners(self.model,self.copy,'held')
        np.testing.assert_allclose([.02,.16,.02],np.ptp(points,axis=0),atol=1e-12,rtol=0)

    def test_moving_copy_preserves_original(self):
        before=self.original.qpos.copy()
        place(self.model,self.copy,source='held',initial=self.pose,grasp=self.pose,release=sm.SE3(1.,2.,3.))
        np.testing.assert_array_equal(before,self.original.qpos)
        np.testing.assert_allclose([1.,2.,3.],self.copy.body('held').xpos,atol=1e-12,rtol=0)


if __name__=='__main__':
    unittest.main(verbosity=2)

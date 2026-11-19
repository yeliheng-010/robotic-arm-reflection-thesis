"""世界偏航与保持位置的行为约束。"""
import unittest
import numpy as np
import spatialmath as sm
from posecheck.adapter import options


class PoseTests(unittest.TestCase):
    def setUp(self):
        self.start = sm.SE3.Trans(1,2,3)*sm.SE3.Ry(.4)
        self.values = dict(T_start=self.start,target=(1.42,1.03,.86),keep_orientation=True)

    def test_zero_yaw_preserves_original_call(self):
        value = options(self.values,0)
        self.assertEqual(self.values,value)
        self.assertIsNot(self.values,value)

    def test_world_yaw_preserves_position_and_rotates_orientation(self):
        value = options(self.values,90)
        np.testing.assert_allclose([1.42,1.03,.86],value['target'].t)
        np.testing.assert_allclose((sm.SO3.Rz(90,unit='deg')*sm.SO3(self.start.R)).R,value['target'].R)
        self.assertFalse(value['keep_orientation'])
        self.assertEqual((1.42,1.03,.86),self.values['target'])
        self.assertTrue(self.values['keep_orientation'])

    def test_signed_yaw_preserves_world_vertical_component(self):
        for angle in (-90,-45,45,90):
            value = options(self.values,angle)
            np.testing.assert_allclose(self.start.R[2],value['target'].R[2],atol=1e-12)

    def test_unregistered_yaw_is_rejected(self):
        with self.assertRaises(ValueError):
            options(self.values,180)


if __name__=='__main__':
    unittest.main()

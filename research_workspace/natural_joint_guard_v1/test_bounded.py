import math
import unittest
import numpy as np
from bounded_ik import representatives


class BoundsTests(unittest.TestCase):
    def bounds(self):
        limits = np.tile([-6.2831,6.2831],(6,1))
        limits[2] = [-3.1415,3.1415]
        return limits

    def test_elbow_equivalent_inside_hardware_limits(self):
        q = np.array([1.,.2,4.068317875213403,.4,-4.2,-1.1])
        actual = representatives(q,q,self.bounds())
        self.assertAlmostEqual(q[2]-2*math.pi,actual[2])
        self.assertTrue(np.all(actual>=self.bounds()[:,0]))
        self.assertTrue(np.all(actual<=self.bounds()[:,1]))
        np.testing.assert_allclose(np.sin(q),np.sin(actual),atol=1e-12)
        np.testing.assert_allclose(np.cos(q),np.cos(actual),atol=1e-12)

    def test_valid_nearest_angle_is_preserved(self):
        q = np.array([1.,.2,2.,.4,-4.2,-1.1])
        np.testing.assert_array_equal(q,representatives(q,q,self.bounds()))

    def test_no_representative_or_nonfinite_rejected(self):
        q = np.zeros(6)
        q[2] = math.pi
        self.assertEqual(0,len(representatives(q,q,self.bounds())))
        q[2] = float('nan')
        self.assertEqual(0,len(representatives(q,q,self.bounds())))
        self.assertEqual(0,len(representatives([],np.zeros(6),self.bounds())))


if __name__ == '__main__':
    unittest.main()

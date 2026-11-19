import math
import unittest
from jr_angles import candidates


class AngleTests(unittest.TestCase):
    def test_keeps_both_turn_directions(self):
        rows = candidates([0.,0.],[-3.,-4.7],bounds=[[-6.28,6.28]]*2)
        self.assertEqual(4,len(rows))
        self.assertIn([-3.,-4.7],rows)
        self.assertIn([-3.+2*math.pi,-4.7+2*math.pi],rows)
        self.assertEqual([-3.,-4.7+2*math.pi],rows[0])

    def test_respects_joint_limit_and_equivalence(self):
        start,goal = [0.]*6,[-3.,-.4,-2.,.5,-4.7,2.2]
        bounds = [[-6.28,6.28]]*6
        bounds[2] = [-3.1415,3.1415]
        rows = candidates(start,goal,bounds=bounds)
        self.assertEqual(32,len(rows))
        self.assertEqual(32,len(set(map(tuple,rows))))
        for row in rows:
            self.assertTrue(all(low<=q<=high for q,(low,high) in zip(row,bounds)))
            self.assertTrue(all(abs(math.remainder(q-g,2*math.pi))<1e-12 for q,g in zip(row,goal)))

    def test_missing_representative_rejects(self):
        self.assertEqual([],candidates([0.],[2.],bounds=[[-1.,1.]]))

    def test_rejects_nonfinite_and_invalid_dimensions(self):
        for args in (([0.],[float('nan')],[[-1.,1.]]),([0.],[0.],[[1.,-1.]]),
                     ([0.],[0.,1.],[[-1.,1.]])):
            with self.subTest(args=args),self.assertRaises(ValueError):
                candidates(args[0],args[1],bounds=args[2])


if __name__ == '__main__':
    unittest.main(verbosity=2)

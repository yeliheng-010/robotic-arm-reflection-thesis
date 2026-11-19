import unittest
from goal_policy import usable_half


class PolicyTests(unittest.TestCase):
    def test_reserves_object_extent_and_edge_margin(self):
        actual=usable_half([.128,.108],[.04,.03])
        self.assertAlmostEqual(.068,actual[0])
        self.assertAlmostEqual(.058,actual[1])

    def test_oversize_object_rejected(self):
        with self.assertRaises(ValueError):
            usable_half([.1,.1],[.09,.04])


if __name__=='__main__':
    unittest.main()

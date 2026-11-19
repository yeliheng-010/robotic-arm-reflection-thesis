import unittest
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from goal_geometry import targets
from goal_policy import EDGE_MARGIN_M


class GeometryTests(unittest.TestCase):
    def test_all_goals_keep_entire_object_inside(self):
        geometry=dict(source_center=[1.,.5,.8],source_half=[.04,.03,.038],
                      bin_center=[.9,.4,.75],interior_half=[.128,.108],
                      usable_half=[.068,.058],wall_top=.9)
        pose=sm.SE3(1.01,.49,.85)
        rows=list(targets(pose,geometry))
        self.assertEqual(27,len(rows))
        for row in rows:
            center=np.array(row['object_center'])
            expected=center+pose.t-np.array(geometry['source_center'])
            np.testing.assert_allclose(expected,row['target'],atol=1e-12)
            occupancy=np.abs(center[:2]-geometry['bin_center'][:2])+geometry['source_half'][:2]
            self.assertTrue(np.all(occupancy<=np.array(geometry['interior_half'])-EDGE_MARGIN_M+1e-12))
            self.assertAlmostEqual(row['bottom_gap'],center[2]-.038-.9)


if __name__=='__main__':
    unittest.main()

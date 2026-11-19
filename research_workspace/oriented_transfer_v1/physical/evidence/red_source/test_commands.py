import unittest
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from cc_common import read
from commands import build

ROOT=__import__('pathlib').Path(__file__).resolve().parents[1]
PLAN=ROOT/'path_v2/results/audit/capsule_964345/plan.json'


class CommandsTests(unittest.TestCase):
    def test_preserves_certified_joint_path_timing_and_release_orientation(self):
        selected=read(PLAN)['selected']
        planners,times,poses=build(selected,1.5)
        self.assertEqual([1.5,*selected['route']['durations']],times)
        self.assertEqual(2,len(planners))
        np.testing.assert_array_equal(selected['route']['waypoints'][0],planners[1].interpolate(0.))
        np.testing.assert_allclose(selected['route']['waypoints'][-1],planners[1].interpolate(times[1]),atol=1e-12,rtol=0)
        np.testing.assert_array_equal(selected['goal']['release'],poses[-1].A)
        self.assertFalse(np.allclose(selected['prefix']['pose'],poses[-1].A))

    def test_preserves_original_lift_and_start(self):
        selected=read(PLAN)['selected']
        planners,times,poses=build(selected,1.5)
        start=sm.SE3(np.array(selected['prefix']['pose']))
        np.testing.assert_allclose(start.A,planners[0].interpolate(0.).A,atol=1e-12,rtol=0)
        np.testing.assert_allclose(start.t+[0,0,selected['lift']],poses[0].t,atol=1e-12,rtol=0)


if __name__=='__main__':
    unittest.main(verbosity=2)

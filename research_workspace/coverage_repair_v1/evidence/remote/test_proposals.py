import copy
import unittest
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from sd_camera import BASE_POSITION, TARGET
from proposals import cameras, grasps


class ProposalTests(unittest.TestCase):
    def test_camera_changes_stay_in_original_bounds(self):
        boxes = {'object': [[1., .4, .7], [1.4, .8, .9]]}
        anchor = dict(azimuth_offset_deg=0., elevation_deg=70., distance_m=1.1,
            fovy=60., target=[1.2, .6, .8], position=[0., 0., 1.], rotation=np.eye(3).tolist())
        original = copy.deepcopy(anchor)
        rows = cameras([anchor], boxes, previous=[])
        self.assertGreater(len(rows), 0)
        self.assertLessEqual(len(rows), 128)
        self.assertEqual(original, anchor)
        scale = np.linalg.norm(BASE_POSITION-TARGET)
        for row in rows:
            self.assertLessEqual(abs(row['azimuth_offset_deg']), 60.)
            self.assertTrue(35. <= row['elevation_deg'] <= 75.)
            self.assertTrue(.8*scale <= row['distance_m'] <= 1.3*scale)
            self.assertTrue(48. <= row['fovy'] <= 65.)
            self.assertLessEqual(np.max(np.abs(np.array(row['target'])[:2]-[1.2,.6])), .1)
            np.testing.assert_allclose(np.eye(3), np.array(row['rotation']).T@row['rotation'], atol=1e-12)

    def test_camera_previous_candidates_never_repeat(self):
        boxes = {'object': [[1., .4, .7], [1.4, .8, .9]]}
        anchor = dict(azimuth_offset_deg=0., elevation_deg=70., distance_m=1.1,
            fovy=60., target=[1.2,.6,.8])
        rows = cameras([anchor], boxes, previous=[])
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows, cameras([anchor], boxes, previous=[]))
        self.assertEqual([], cameras([anchor], boxes, previous=rows))

    def test_tilted_grasps_keep_observed_translation(self):
        fitted = dict(available=True, center=[0.,0.,.1], closing_axis=[1.,0.,0.],
            top_z_m=.13, width_m=.02, length_m=.12)
        nominal = sm.SE3.Trans(0.,0.,.1)
        rows = grasps(nominal, fitted)
        self.assertGreater(len(rows), 0)
        self.assertLessEqual(len(rows), 128)
        for row in rows:
            self.assertLessEqual(np.linalg.norm(row['pose'].t-nominal.t), .05)
            self.assertIn(abs(row['angle_deg']), (15.,30.))
            self.assertIn(row['axis'], ('y','z'))
            np.testing.assert_allclose(np.eye(3), row['pose'].R.T@row['pose'].R, atol=1e-12)

    def test_no_grasp_without_available_observation(self):
        self.assertEqual([], grasps(sm.SE3(), {'available': False}))


if __name__ == '__main__':
    unittest.main(verbosity=2)

import unittest
import numpy as np
from qualification_data import projection


class ProjectionTests(unittest.TestCase):
    def test_out_of_frame_and_other_root_are_rejected(self):
        calibration = dict(camera_transform=np.eye(4).tolist(), intrinsics=[10,10,5,5])
        roots = np.ones((10,10), dtype=int)
        self.assertFalse(projection([0,1,1], calibration, shape=roots.shape, roots=roots, body_id=1)['passed'])
        self.assertFalse(projection([0,0,1], calibration, shape=roots.shape, roots=roots, body_id=2)['passed'])
        self.assertTrue(projection([0,0,1], calibration, shape=roots.shape, roots=roots, body_id=1)['passed'])

    def test_behind_camera_rejected(self):
        calibration = dict(camera_transform=np.eye(4).tolist(), intrinsics=[10,10,5,5])
        self.assertFalse(projection([0,0,-1], calibration, shape=(10,10), roots=np.ones((10,10)), body_id=1)['passed'])

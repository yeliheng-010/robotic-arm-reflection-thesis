import unittest
import numpy as np
from model_grasp_gpu_v1.observed import prepare


def fixture():
    depth = np.full((20, 20), 1.)
    mask = np.zeros(depth.shape, dtype=bool)
    mask[4:14, 4:14] = True
    v, u = np.where(mask)
    points = np.column_stack(((u-10)/100, (v-10)/100, depth[v, u]))
    arrays = dict(depth=depth, mask=mask, camera_points=points, world_points=points.copy())
    calibration = dict(transform=np.eye(4).tolist(), intrinsics=[100.,100.,10.,10.])
    return arrays, calibration


class ObservationTests(unittest.TestCase):
    def test_target_array_unchanged_and_scene_excludes_target(self):
        arrays, calibration = fixture()
        result = prepare(arrays, calibration, [0.,0.,1.])
        self.assertIsNotNone(result)
        np.testing.assert_array_equal(arrays['world_points'], result['target_points'])
        self.assertEqual(300, len(result['scene_points']))
        self.assertEqual({'qualified','revision','target_points','scene_points','nominal'}, set(result))

    def test_calibration_mismatch_rejected(self):
        arrays, calibration = fixture()
        calibration['transform'][0][3] = .1
        with self.assertRaises(ValueError):
            prepare(arrays, calibration, [0.,0.,1.])

    def test_invalid_depth_is_not_an_obstacle_point(self):
        arrays, calibration = fixture()
        arrays['depth'][0,0] = np.nan
        arrays['depth'][0,1] = 0.
        result = prepare(arrays, calibration, [0.,0.,1.])
        self.assertIsNotNone(result)
        self.assertEqual(298, len(result['scene_points']))

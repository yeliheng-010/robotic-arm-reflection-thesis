import unittest
import numpy as np
from sd_camera import look_at
from sf_camera import framed, corners
from observation_search_v1.framing import recenter, image_center
from observation_search_v1.candidates import anchors, deltas, batch


def camera(azimuth=0.):
    target = np.array([1.255, .6, .8])
    az, el = np.deg2rad([180+azimuth, 65.])
    position = target + 1.3*np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])
    return dict(position=position.tolist(), target=target.tolist(), rotation=look_at(position, target).tolist(),
                fovy=60., azimuth_offset_deg=azimuth, elevation_deg=65., distance_m=1.3)


def row(index, azimuth):
    return dict(index=index, camera=camera(azimuth), measurements=dict(Apple=dict(pixels=500, short_side=20)),
        gate=dict(rejected=['Apple'], objects=dict(Apple=dict(visible_fraction=1., component_fraction=1.,
                                                           reasons=['pixels']))))


class CandidateTests(unittest.TestCase):
    def test_anchors_prefer_distinct_direction_before_near_duplicate(self):
        self.assertEqual([0, 2], [r['index'] for r in anchors([row(0, 0), row(1, 1), row(2, 40)])][:2])

    def test_pixel_failure_prioritizes_distance(self):
        self.assertLess(deltas(row(0, 0), 0)[1][2], 0)
        np.testing.assert_allclose(deltas(row(0, 0), 0)[1]/2, deltas(row(0, 0), 1)[1])

    def test_recentering_improves_center_and_preserves_bounds(self):
        boxes = dict(item=[[1., .4, .7], [1.35, .8, .9]])
        center = np.array([1.175, .6, .8])
        before = camera()
        after = recenter(before, boxes, center)
        self.assertIsNotNone(after)
        self.assertTrue(framed(boxes, after)['passed'])
        self.assertTrue(48 <= after['fovy'] <= 65)
        self.assertTrue(np.all(np.abs(np.asarray(after['target'][:2])-center[:2]) <= .10000001))
        points = corners(boxes['item'])
        self.assertLess(np.linalg.norm(image_center(after, points)-320),
                        np.linalg.norm(image_center(before, points)-320))

    def test_truth_is_not_used_and_candidates_are_unique(self):
        boxes = dict(item=[[1., .4, .7], [1.35, .8, .9]])
        rows = [row(0, 0), row(1, 30)]
        first = batch(rows, boxes, 0)
        for item in rows:
            item['private_truth'] = dict(center=[999, 999, 999], successful=True)
        self.assertEqual(first, batch(rows, boxes, 0))
        self.assertLessEqual(len(first), 32)
        self.assertGreater(len(first), 0)
        self.assertEqual(len(first), len({str(r['camera']) for r in first}))

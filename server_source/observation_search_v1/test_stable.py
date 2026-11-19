import unittest
import numpy as np
from observation_search_v1.stable import settle, encode, decode


class StableTests(unittest.TestCase):
    def run_frames(self, values):
        frames = iter(np.full((100, 100, 3), v, dtype=np.uint8) for v in values)
        return settle(lambda: next(frames))

    def test_stale_first_frame_requires_two_later_passes(self):
        frames, result = self.run_frames([54, 0, 0, 0])
        self.assertTrue(result['passed'])
        self.assertEqual(4, result['count'])
        self.assertFalse(result['checks'][0]['passed'])
        self.assertEqual(0, int(frames[-1][0, 0, 0]))

    def test_one_late_pass_is_insufficient(self):
        _, result = self.run_frames([0, 54, 0, 0])
        self.assertFalse(result['passed'])
        self.assertEqual(4, result['count'])

    def test_stable_stops_at_three_without_extra_render(self):
        _, result = self.run_frames([0, 0, 0])
        self.assertTrue(result['passed'])
        self.assertEqual(3, result['count'])

    def test_packed_evidence_is_lossless_at_uint8_boundaries(self):
        frames = [np.full((2, 2, 3), v, dtype=np.uint8) for v in (0, 255, 0, 255)]
        for expected, actual in zip(frames, decode(encode(frames)), strict=True):
            np.testing.assert_array_equal(expected, actual)

import unittest
from types import SimpleNamespace
import numpy as np
from qualified_model_v1.segmentation import select, world_points


class Tensor:
    def __init__(self, value):
        self.value = np.asarray(value)

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.value


class SegmentationTests(unittest.TestCase):
    def test_no_roi_fallback(self):
        mask, report = select([], shape=(3, 3), point=[1, 1])
        self.assertIsNone(mask)
        self.assertFalse(report['accepted'])

    def test_only_model_point_and_confidence_select(self):
        masks = [Tensor(np.eye(3)), Tensor(np.ones((3, 3))), Tensor(np.zeros((3, 3)))]
        row = SimpleNamespace(masks=SimpleNamespace(data=masks),
                              boxes=SimpleNamespace(conf=Tensor([.8, .7, 1.])))
        mask, report = select([row], shape=(3, 3), point=[1, 1])
        np.testing.assert_array_equal(np.eye(3).astype(bool), mask)
        self.assertEqual(0, report['selected_index'])

    def test_projection_ignores_dropout(self):
        calibration = dict(intrinsics=[2, 2, 0, 0], transform=np.eye(4).tolist())
        points = world_points(np.array([[0., 1.]]), np.ones((1, 2), bool), calibration=calibration)
        np.testing.assert_array_equal([[.5, 0., 1.]], points)


if __name__ == '__main__':
    unittest.main()

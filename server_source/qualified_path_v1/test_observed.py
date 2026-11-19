import unittest
from types import SimpleNamespace
import numpy as np
from qualified_path_v1.observed import build, targets


def clouds():
    x, y = np.meshgrid(np.linspace(-.16, .16, 35), np.linspace(-.14, .14, 35))
    floor = np.column_stack((x.ravel(), y.ravel(), np.zeros(x.size)))
    rim = floor.copy()
    rim[:, 2] = .10
    source = np.tile([[-.06, -.02, .00], [.06, .02, .03], [-.06, .02, .01], [.06, -.02, .02]], (50, 1))
    return source, np.concatenate([floor, rim])


class ObservedTests(unittest.TestCase):
    def test_translation_changes_targets_from_observations(self):
        source, container = clouds()
        first = build(source, container, anchor=[0, 0, 0])
        shift = np.array([.7, -.4, .75])
        second = build(source+shift, container+shift, anchor=shift)
        p1 = next(targets(SimpleNamespace(t=np.zeros(3)), first))['target']
        p2 = next(targets(SimpleNamespace(t=shift), second))['target']
        np.testing.assert_allclose(np.array(p1)+shift, p2, atol=1e-12, rtol=0)

    def test_missing_rim_rejected(self):
        source, container = clouds()
        with self.assertRaisesRegex(ValueError, 'rim_not_observed'):
            build(source, container[container[:, 2] == 0], anchor=[0, 0, 0])

    def test_object_does_not_fit_rejected(self):
        source, container = clouds()
        source[:, :2] *= 10
        with self.assertRaisesRegex(ValueError, 'object_margin'):
            build(source, container, anchor=[0, 0, 0])

    def test_noisy_outlier_does_not_set_rim(self):
        source, container = clouds()
        container = np.concatenate([container, [[0, 0, 10]]])
        self.assertAlmostEqual(.10, build(source, container, anchor=[0, 0, 0])['rim_z'])


if __name__ == '__main__':
    unittest.main()

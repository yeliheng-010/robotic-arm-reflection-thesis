import math
import unittest
from pose_fresh_v1.policy import pairs


def view(index, degrees, valid=True):
    theta = math.radians(degrees)
    return dict(index=index, calibration_passed=valid,
                camera=dict(position=[math.cos(theta), math.sin(theta), 0.], target=[0., 0., 0.]))


class PolicyTests(unittest.TestCase):
    def test_separation_and_budget_are_preserved(self):
        rows = [view(i, degree) for i, degree in enumerate([0, 5, 20, 40, 60])]
        self.assertEqual([(0, 2), (0, 3), (0, 4)], pairs(rows))

    def test_uncalibrated_views_are_never_selected(self):
        self.assertEqual([], pairs([view(0, 0), view(1, 30, False)]))

    def test_no_pair_when_viewpoints_too_close(self):
        self.assertEqual([], pairs([view(0, 0), view(1, 8)]))

    def test_pair_choice_does_not_depend_on_truth(self):
        rows = [dict(view(0, 0), accurate=False), dict(view(1, 20), accurate=True)]
        self.assertEqual([(0, 1)], pairs(rows))


if __name__ == "__main__":
    unittest.main()

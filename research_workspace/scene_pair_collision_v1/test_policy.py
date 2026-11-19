import unittest
from collision_policy import eligible, ordered


def report(error, phase):
    return dict(error_type=error, evidence=dict(motion_context=dict(phase=phase)))


class PolicyTests(unittest.TestCase):
    def test_grasp_collision_enables_reorder(self):
        self.assertTrue(eligible(report('collision', 'grasp_pose')))
        self.assertTrue(eligible(report('collision', 'grasp_approach')))

    def test_other_failures_and_held_object_collisions_are_unchanged(self):
        for value in (None, {}, report('object_dropped', 'carry_lift'),
                      report('collision', 'carry_lift'), report('collision', 'carry_transport')):
            self.assertFalse(eligible(value))

    def test_original_remains_fallback_and_input_is_unmodified(self):
        rows = [dict(id='original'), dict(id='world_down_0'), dict(id='world_down_180')]
        self.assertEqual(['world_down_0', 'world_down_180', 'original'], [x['id'] for x in ordered(rows)])
        self.assertEqual('original', rows[0]['id'])

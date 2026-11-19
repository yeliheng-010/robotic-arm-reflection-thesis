import unittest
from policy import eligible,snapshot


class EligibilityTests(unittest.TestCase):
    def test_planning_collision_never_counts_as_natural(self):
        error=dict(error_type='collision',evidence=dict(route_planning_rejected=True))
        self.assertEqual((False,'planning_rejection'),eligible(dict(error=error)))

    def test_real_grasp_failure_and_engine_error_distinguished(self):
        self.assertTrue(eligible(dict(error=dict(error_type='empty_grasp')))[0])
        self.assertFalse(eligible(dict(error=dict(error_type='unknown')))[0])

    def test_new_noise_or_seed_does_not_duplicate_same_physics(self):
        base=dict(private=[dict(state_sha256='state',clean_sha256='clean',noisy_sha256='noise1')])
        other=dict(private=[dict(state_sha256='state',clean_sha256='clean',noisy_sha256='noise2')])
        one=dict(source='RedBlock',destination='BlueBin',seed=1)
        two=dict(one,seed=2)
        self.assertEqual(snapshot(one,base),snapshot(two,other))


if __name__=='__main__':
    unittest.main()

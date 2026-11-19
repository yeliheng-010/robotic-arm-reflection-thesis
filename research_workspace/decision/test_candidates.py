"""测量到候选的边界和来源契约。"""
import copy
import unittest

from reflection.reflector import Parameters
from decision.candidates import build_candidates


def report(evidence):
    return {'stage': 'execution', 'evidence': evidence}


class CandidateTests(unittest.TestCase):
    def test_absolute_alignment_uses_current_offset(self):
        params = Parameters(grasp_offset=(.02, -.01, .03))
        rows = build_candidates(report({'grasp_residual_xy': [.01, -.04]}), params, source='RedBlock')
        self.assertIn('align_grasp', [x['id'] for x in rows])
        change = next(x for x in rows if x['id'] == 'align_grasp')['changes']['grasp_offset']
        self.assertEqual([.01, .03, .03], change)

    def test_release_correction_opposes_residual(self):
        rows = build_candidates(report({'placement_residual_xy': [-.18, .02]}), Parameters(), source='RedBlock')
        self.assertIn('align_release', [x['id'] for x in rows])
        self.assertEqual([.18, -.02, 0], next(x for x in rows if x['id'] == 'align_release')['changes']['place_offset'])

    def test_clearance_uses_payload_bottom_and_obstacle_top(self):
        evidence = {'diagnostics': {'contact_bounds_world': [
            {'body': 'RedBlock', 'lower_xyz': [0, 0, 1.08], 'upper_xyz': [1, 1, 1.16]},
            {'body': 'Wall', 'lower_xyz': [0, 0, .7], 'upper_xyz': [1, 1, 1.12]}]}}
        rows = build_candidates(report(evidence), Parameters(), source='RedBlock')
        self.assertIn('clear_contact', [x['id'] for x in rows])
        self.assertAlmostEqual(.44, next(x for x in rows if x['id'] == 'clear_contact')['changes']['lift_height'])

    def test_out_of_range_correction_is_omitted_not_clipped(self):
        rows = build_candidates(report({'placement_residual_xy': [-.4, 0]}), Parameters(), source='RedBlock')
        self.assertNotIn('align_release', [x['id'] for x in rows])

    def test_missing_or_nonfinite_measurement_produces_no_alignment(self):
        for residual in (None, [float('nan'), 0], [True, 0], [1], 'bad'):
            rows = build_candidates(report({'grasp_residual_xy': residual}), Parameters(), source='RedBlock')
            self.assertNotIn('align_grasp', [x['id'] for x in rows])

    def test_zero_residual_is_not_an_effective_correction(self):
        rows = build_candidates(report({'grasp_residual_xy': [0, 0]}), Parameters(), source='RedBlock')
        self.assertNotIn('align_grasp', [x['id'] for x in rows])

    def test_input_is_not_mutated(self):
        original = report({'placement_residual_xy': [-.18, .02]})
        saved = copy.deepcopy(original)
        build_candidates(original, Parameters(), source='RedBlock')
        self.assertEqual(saved, original)


if __name__ == '__main__':
    unittest.main()

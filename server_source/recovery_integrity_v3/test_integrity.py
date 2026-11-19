import copy
import unittest
from unittest.mock import patch
from iv3_audit import inspect
from iv3_geometry import strict_compare, ReconstructionMismatch
from geometry_consistency import REBUILD_ATOL_M
from ig_policy import execution_mode
import geometry_v3


def sample():
    return dict(source_center=[0., 0., 0.], source_half=[.02, .02, .02],
        bin_center=[0., 0., 0.], interior_half=[.1, .1], usable_half=[.06, .06], wall_top=.2)


class IntegrityTests(unittest.TestCase):
    def test_exact_and_original_boundary_pass(self):
        cached, current = sample(), sample()
        current['source_center'][1] = REBUILD_ATOL_M
        self.assertEqual(REBUILD_ATOL_M, strict_compare(cached, current)['max_abs_m'])

    def test_over_boundary_is_typed_rejection(self):
        cached, current = sample(), sample()
        current['source_center'][1] = 1.0726079329170801e-6
        with self.assertRaises(ReconstructionMismatch) as caught:
            strict_compare(cached, current)
        self.assertEqual({'source_center': current['source_center'][1]}, caught.exception.evidence['exceeded'])

    def test_static_difference_remains_unknown_error(self):
        current = sample()
        current['wall_top'] += 1e-9
        with self.assertRaises(AssertionError):
            strict_compare(sample(), current)

    def test_nonfinite_and_wrong_shape_fail(self):
        for invalid in ([float('nan'), 0., 0.], [0., 0.]):
            current = sample()
            current['source_center'] = invalid
            with self.assertRaises(AssertionError):
                strict_compare(sample(), current)

    def test_compare_does_not_change_inputs(self):
        original = sample()
        before = copy.deepcopy(original)
        strict_compare(original, sample())
        self.assertEqual(before, original)

    def test_partial_case_is_not_reexecuted(self):
        with self.assertRaises(AssertionError):
            execution_mode(folder_exists=True, completed=False)
        self.assertEqual('execute_new', execution_mode(folder_exists=False, completed=False))
        self.assertEqual('audit_existing', execution_mode(folder_exists=True, completed=True))

    def test_unknown_audit_failure_propagates(self):
        with patch('ig_audit.inspect', side_effect=RuntimeError('unknown')):
            with self.assertRaises(RuntimeError):
                inspect({})


if __name__ == '__main__':
    unittest.main()

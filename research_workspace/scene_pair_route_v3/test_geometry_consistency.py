"""真实差异回归及越界/非有限值反例；纯CPU，无物理推进。"""
import copy
import json
from pathlib import Path
import unittest
from geometry_consistency import compare


class ConsistencyTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('geometry_diagnostic.json')
        self.rows = json.loads(path.read_text(encoding='utf-8'))

    def test_measured_submicron_reconstruction(self):
        for row in self.rows:
            result = compare(row['recorded'], row['reconstructed'])
            self.assertAlmostEqual(row['max_abs_m'], result['max_abs_m'])

    def test_reject_dynamic_shift_over_one_micron(self):
        expected = self.rows[0]['recorded']
        for key in ('source_center', 'source_half', 'usable_half'):
            actual = copy.deepcopy(expected)
            actual[key][0] += 1.01e-6
            with self.assertRaises(AssertionError):
                compare(expected, actual)

    def test_static_geometry_remains_exact(self):
        expected = self.rows[0]['recorded']
        for key in ('bin_center', 'interior_half'):
            actual = copy.deepcopy(expected)
            actual[key][0] += 1e-9
            with self.assertRaises(AssertionError):
                compare(expected, actual)
        actual = dict(expected, wall_top=expected['wall_top'] + 1e-9)
        with self.assertRaises(AssertionError):
            compare(expected, actual)

    def test_reject_nonfinite_and_shape_change(self):
        expected = self.rows[0]['recorded']
        for value in (float('nan'), float('inf'), [1., 2.]):
            actual = copy.deepcopy(expected)
            actual['source_center'] = value
            with self.assertRaises(AssertionError):
                compare(expected, actual)

    def test_reject_missing_or_unknown_field(self):
        expected = self.rows[0]['recorded']
        missing = dict(expected)
        missing.pop('wall_top')
        for actual in (missing, dict(expected, unknown=0.)):
            with self.assertRaises(AssertionError):
                compare(expected, actual)


if __name__ == '__main__':
    unittest.main()

"""仅从已提供观测计算几何关系，不能产生修正参数。"""
import copy
import unittest
from stability.relations_prompt import add_relations


class RelationTests(unittest.TestCase):
    def test_uses_measured_boxes_not_commanded_tcp_as_object_position(self):
        report = {'evidence': {'contacts': [['Block', 'Wall']], 'diagnostics': {
            'commanded_tcp_xyz': [1.287, .297, 1.163],
            'contact_bounds_world': [
                {'body': 'Block', 'lower_xyz': [1.138, .3634, 1.0803],
                 'upper_xyz': [1.2267, .4396, 1.16]},
                {'body': 'Wall', 'lower_xyz': [.86, .34, .739],
                 'upper_xyz': [1.54, .367, 1.12]}]}}}
        before = copy.deepcopy(report)
        output = add_relations(report)
        relation = output['evidence']['body_aabb_relations'][0]
        self.assertEqual([False, False], relation['commanded_tcp_inside_each_aabb'])
        self.assertAlmostEqual(-.0397, relation['first_bottom_minus_second_top_z'])
        for expected, actual in zip([.0887, .0036, .0397], relation['overlap_xyz']):
            self.assertAlmostEqual(expected, actual)
        self.assertEqual(before, report)
        self.assertNotIn('changes', output)

    def test_missing_bounds_does_not_invent_geometry(self):
        report = {'evidence': {'contacts': [['Block', 'Wall']]}}
        self.assertEqual([], add_relations(report)['evidence']['body_aabb_relations'])


if __name__ == '__main__':
    unittest.main()

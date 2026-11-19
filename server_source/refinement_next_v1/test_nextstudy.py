"""检验实验隔离、实际参数语义和门槛，避免错误扩大实验。"""
import copy
import unittest
from controlled.config import scenario
from nextstudy.design import compose_mixed, physical_items
from nextstudy.fixtures import fixtures
from nextstudy.semantic import action_check, gate


class DesignTests(unittest.TestCase):
    def test_feedback_toggle_does_not_change_physics_or_depth(self):
        on = compose_mixed(82100, layout=True, physics=True, feedback=True)
        off = compose_mixed(82100, layout=True, physics=True, feedback=False)
        self.assertEqual(on['bodies'], off['bodies'])
        self.assertEqual(on['profile'], off['profile'])
        self.assertNotEqual(on['feedback'], off['feedback'])

    def test_full_mixed_recovers_original(self):
        self.assertEqual(scenario(82100, 'mixed'),
                         compose_mixed(82100, layout=True, physics=True, feedback=True))

    def test_physics_toggle_keeps_layout(self):
        off = compose_mixed(82100, layout=True, physics=False, feedback=True)
        original = scenario(82100, 'mixed')
        for name, body in off['bodies'].items():
            self.assertEqual(original['bodies'][name]['xy'], body['xy'])
            self.assertEqual(1, body['density_scale'])
            self.assertEqual(1, body['friction_scale'])
        self.assertEqual(original['profile']['depth_sigma_m'], off['profile']['depth_sigma_m'])

    def test_complete_factorial_and_legal_parameters(self):
        from reflection.reflector import Parameters
        rows = physical_items([.038224, -.002488])
        self.assertEqual(40, len(rows))
        self.assertEqual(40, len({r['id'] for r in rows}))
        self.assertEqual({7:12, 25:6, 37:6, 47:16},
                         {c:sum(r['case']==c for r in rows) for c in (7,25,37,47)})
        for row in rows:
            Parameters().updated(row['parameters'])


class SemanticTests(unittest.TestCase):
    def test_nonzero_current_requires_new_absolute_value(self):
        item = next(f for f in fixtures() if f['id']=='absolute_grasp_positive')
        self.assertTrue(action_check(item, {'grasp_offset':[.04, .01, 0]})['passed'])
        self.assertFalse(action_check(item, {'grasp_offset':[-.02, .03, 0]})['passed'])

    def test_saturation_is_in_expected_answer_not_response_repair(self):
        item = next(f for f in fixtures() if f['id']=='bound_place_positive')
        self.assertTrue(action_check(item, {'place_offset':[-.25, 0, 0]})['passed'])
        self.assertFalse(action_check(item, {'place_offset':[-.31, 0, 0]})['passed'])

    def test_missing_and_stage_mismatch_have_no_invented_target(self):
        items = [f for f in fixtures() if f['group']=='missing_or_stage']
        self.assertEqual(4, len(items))
        self.assertTrue(all(f['expected'] is None for f in items))
        item = next(f for f in items if f['id']=='stage_pregrasp')
        self.assertFalse(action_check(item, {'lift_height':.45})['passed'])

    def test_gate_requires_complete_and_reviewed_results(self):
        rows = [dict(legal=True, action_check={'passed':True}, service_error=False,
                     rationale_review='passed') for _ in range(48)]
        self.assertTrue(gate(rows))
        self.assertFalse(gate(rows[:-1]))
        rows[0]['rationale_review'] = 'pending'
        self.assertFalse(gate(rows))


if __name__ == '__main__':
    unittest.main()

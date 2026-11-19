"""验证硬边界、可见证据和来源；不以模型偶然成功代替测试。"""
import importlib
import importlib.util
import json
import unittest
from reflection.reflector import Parameters
from nextstudy.fixtures import fixtures


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('bounded.candidates'), 'Candidate implementation missing')
        self.c = importlib.import_module('bounded.candidates')
        self.s = importlib.import_module('bounded.selection')

    def item(self, name):
        return next(f for f in fixtures() if f['id']==name)

    def options(self, name):
        f = self.item(name)
        return self.c.candidates(f['report'],f['parameters'],[])

    def test_nonzero_absolute_and_preserved_z(self):
        f = self.item('absolute_grasp_positive')
        f['parameters']['grasp_offset'] = [.06,-.02,.015]
        rows = self.c.candidates(f['report'],f['parameters'],[])
        measured = next(r for r in rows if r['kind']=='measured_grasp')
        self.assertEqual([.04,.01,.015],measured['changes']['grasp_offset'])

    def test_bounds_and_explanation_match_actual_value(self):
        row = next(r for r in self.options('bound_place_negative') if r['kind']=='measured_place')
        self.assertEqual([.25,0.,0.],row['changes']['place_offset'])
        self.assertEqual(.25,row['facts']['new_value'][0])
        self.assertTrue(row['facts']['saturated'][0])
        self.assertIn('0.25',row['explanation'])

    def test_missing_not_invented_as_measured_zero(self):
        rows = self.options('missing_place')
        self.assertTrue(rows)
        self.assertTrue(all(r['kind']=='exploratory_place' for r in rows))
        self.assertTrue(all(r['facts']['measurement'] is None for r in rows))

    def test_stage_mismatch_does_not_use_place_or_lift(self):
        rows = self.options('stage_pregrasp')
        self.assertTrue(all(not set(r['changes']) & {'place_offset','lift_height'} for r in rows))

    def test_every_fixture_candidate_is_legal_and_changes_parameters(self):
        for f in fixtures():
            old = Parameters().updated(f['parameters'])
            for row in self.c.candidates(f['report'],f['parameters'],[]):
                self.assertNotEqual(old,old.updated(row['changes']))
                self.assertEqual('rule_generated_candidate',row['source'])

    def test_hidden_fields_cannot_change_candidates(self):
        f = self.item('sign_grasp_positive')
        before = self.c.candidates(f['report'],f['parameters'],[])
        f['report']['evidence']['hidden_true_position'] = [999,999]
        after = self.c.candidates(f['report'],f['parameters'],[])
        self.assertEqual(before,after)

    def test_invalid_choice_never_falls_back(self):
        rows = self.options('sign_place_positive')
        with self.assertRaises(ValueError):
            self.s.resolve('{"action_id":"unknown"}',rows)
        with self.assertRaises(ValueError):
            self.s.resolve(json.dumps({'action_id':rows[0]['id'],'changes':{'place_offset':[9,0,0]}}),rows)

    def test_valid_choice_preserves_action_and_source(self):
        rows = self.options('sign_place_positive')
        selected = self.s.resolve(json.dumps({'action_id':rows[0]['id']}),rows)
        self.assertEqual(rows[0]['changes'],selected['changes'])
        self.assertEqual('hybrid_llm_selection_rule_candidates_template',selected['source'])

    def test_duplicate_json_keys_rejected(self):
        rows = self.options('sign_place_positive')
        text = '{"action_id":"unknown","action_id":'+json.dumps(rows[0]['id'])+'}'
        with self.assertRaises(ValueError):
            self.s.resolve(text,rows)


if __name__=='__main__':
    unittest.main()

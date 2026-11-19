import unittest
from action_space_audit_v1.catalogue import actions, select
from model_grasp_intent_v1.contract import validate_action
from model_grasp_intent_v1.test_contract import intent
import json


class CatalogueTests(unittest.TestCase):
    def test_all_738_legal_actions_once(self):
        rows = actions()
        self.assertEqual(738,len(rows))
        self.assertEqual(738,len({json.dumps(row,sort_keys=True) for row in rows}))
        for row in rows:
            self.assertEqual(row,validate_action(row))

    def test_top_has_only_one_azimuth(self):
        rows = [r for r in actions() if r['args']['tilt_deg']==0]
        self.assertEqual(18,len(rows))
        self.assertEqual({0},{r['args']['azimuth_deg'] for r in rows})

    def test_select_only_safe_actions_with_direction_diversity(self):
        catalog = [dict(id=str(i),action=intent(tilt_deg=angle)) for i,angle in enumerate((0,0,30,60,90))]
        endpoints = [dict(action_id=str(i),ok=i!=4) for i in range(5)]
        self.assertEqual(['0','2','3'],select(catalog,endpoints,maximum=3))

    def test_no_safe_endpoints_no_path_search(self):
        self.assertEqual([],select([dict(id='0',action=intent())],[],maximum=4))

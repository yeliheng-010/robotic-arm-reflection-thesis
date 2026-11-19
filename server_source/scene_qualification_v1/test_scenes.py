"""拒绝混杂的资格条件，核对单因素隔离。"""
import importlib
import importlib.util
import unittest
from controlled.config import scenario


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('design'),'Scene design missing')
        self.d = importlib.import_module('design')

    def test_position_only_preserves_yaw_physics_and_feedback(self):
        value = self.d.build(905001,'position_only')
        base = scenario(905001,'clean')
        self.assertEqual(base['feedback'],value['feedback'])
        self.assertEqual(base['containers'],value['containers'])
        for name,body in value['bodies'].items():
            self.assertEqual(0,body['yaw_delta'])
            self.assertEqual(1,body['density_scale'])
            self.assertEqual(1,body['friction_scale'])
            self.assertLessEqual(max(abs(a-b) for a,b in zip(body['xy'],base['bodies'][name]['xy'])),.01000001)

    def test_yaw_only_preserves_positions(self):
        value = self.d.build(905001,'yaw_only')
        base = scenario(905001,'clean')
        for name,body in value['bodies'].items():
            self.assertEqual(base['bodies'][name]['xy'],body['xy'])
        self.assertEqual(0,value['profile']['depth_sigma_m'])

    def test_failed_control_never_qualifies(self):
        self.assertFalse(self.d.qualify(False,True,'transport',paired=True))

    def test_wrong_stage_or_wrong_contact_never_qualifies(self):
        self.assertFalse(self.d.qualify(True,True,'descent',paired=True))
        self.assertFalse(self.d.qualify(True,False,'transport',paired=True))

    def test_mismatched_initial_state_never_qualifies(self):
        self.assertFalse(self.d.qualify(True,True,'transport',paired=False))

    def test_predeclared_family_coverage(self):
        rows = self.d.items()
        self.assertEqual(12,len(rows))
        self.assertEqual(12,len({r['id'] for r in rows}))
        self.assertTrue(self.d.qualify(True,True,'transport',paired=True))


if __name__=='__main__':
    unittest.main()

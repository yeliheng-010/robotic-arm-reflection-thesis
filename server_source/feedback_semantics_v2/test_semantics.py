"""阶段定义与几何AABB不能混用根节点的回归测试。"""
import unittest
import numpy as np
from types import SimpleNamespace
from semanticfix2.context import stage_context,enrich
from semanticfix2.telemetry import geom_detail,contact_details
from semanticfix2.design import items


class SemanticsTests(unittest.TestCase):
    def test_guard_early_abort_is_captured(self):
        from unittest.mock import patch
        from reflection.errors import TaskAbort
        from reflection.monitors import abort,ErrorType
        import stability.monitor as guard
        import semanticfix2.telemetry as telemetry
        def fail(monitor):
            abort(ErrorType.COLLISION,'fixture',contacts=[['robot','wall']])
        monitor = SimpleNamespace(env=SimpleNamespace(mj_model=None,mj_data=None))
        with patch.object(guard,'check_environment',fail),patch.object(telemetry,'contact_details',return_value={'captured':True}):
            with telemetry.capture():
                with self.assertRaises(TaskAbort) as caught:
                    guard.check_environment(monitor)
        self.assertEqual({'captured':True},caught.exception.report.evidence['contact_details'])

    def test_place_descent_is_not_grasp_approach(self):
        self.assertEqual('place_descent',stage_context({'action':'move_to_point','motion_segment':'descent'})['phase'])
        self.assertEqual('grasp_approach',stage_context({'action':'move_to_grasp_pose','motion_segment':'approach'})['phase'])

    def test_unknown_combination_remains_unknown(self):
        self.assertEqual('unknown',stage_context({'action':'move_to_grasp_pose','motion_segment':'descent'})['phase'])

    def test_root_and_actual_body_are_distinct(self):
        model = SimpleNamespace(geom_bodyid=np.array([2]),body_rootid=np.array([0,1,1]),
            geom_aabb=np.array([[0,0,0,1,2,3]]),geom_type=np.array([6]),
            geom=lambda i:SimpleNamespace(name='wrist_geom'),
            body=lambda i:SimpleNamespace(name={1:'ur5e_base',2:'wrist_1_link'}[int(i)]))
        data = SimpleNamespace(geom_xpos=np.array([[10,20,30]]),geom_xmat=np.eye(3).reshape(1,9))
        detail = geom_detail(model,data,0)
        self.assertEqual('wrist_1_link',detail['body'])
        self.assertEqual('ur5e_base',detail['root'])
        self.assertEqual([9.,18.,27.],detail['aabb']['low'])
        self.assertEqual([11.,22.,33.],detail['aabb']['high'])

    def test_rotated_noncentered_geom_bounds(self):
        rotation = np.array([[0,-1,0],[1,0,0],[0,0,1]])
        model = SimpleNamespace(geom_bodyid=np.array([0]),body_rootid=np.array([0]),
            geom_aabb=np.array([[1,0,0,1,2,3]]),geom_type=np.array([6]),
            geom=lambda i:SimpleNamespace(name='g'),body=lambda i:SimpleNamespace(name='b'))
        data = SimpleNamespace(geom_xpos=np.array([[10,20,30]]),geom_xmat=rotation.reshape(1,9))
        self.assertEqual([8.,20.,27.],geom_detail(model,data,0)['aabb']['low'])
        self.assertEqual([12.,22.,33.],geom_detail(model,data,0)['aabb']['high'])

    def test_enrichment_preserves_root_contacts_and_does_not_invent_details(self):
        report = dict(error_type='collision',evidence={'contacts':[['ur5e_base','SafetyDivider']],
            'diagnostics':{'action':'move_to_point','motion_segment':'descent'}})
        enriched = enrich(report,attempt=2)
        self.assertEqual(report['evidence']['contacts'],enriched['evidence']['contacts'])
        self.assertNotIn('contact_details',enriched['evidence'])
        self.assertEqual('place_descent',enriched['evidence']['motion_context']['phase'])
        self.assertNotIn('motion_context',report['evidence'])

    def test_manifest_has_22_unique_legal_interventions(self):
        from reflection.reflector import Parameters
        rows = items()
        self.assertEqual(22,len(rows))
        self.assertEqual(22,len({r['id'] for r in rows}))
        for row in rows:
            Parameters().updated(row['parameters'])

    def test_real_mujoco_contact_reports_child_link_geometry(self):
        import mujoco
        xml = '''<mujoco><worldbody>
          <body name="robot"><freejoint/><geom name="base_geom" size=".02"/>
            <body name="wrist" pos=".2 0 0"><geom name="wrist_geom" type="box" size=".08 .08 .08"/></body>
          </body>
          <body name="wall" pos=".3 0 0"><geom name="wall_geom" type="box" size=".08 .08 .08"/></body>
        </worldbody></mujoco>'''
        model = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model,data)
        details = contact_details(model,data,[['robot','wall']])
        self.assertTrue(details['contacts'])
        for contact in details['contacts']:
            self.assertEqual({'wrist','wall'},{g['body'] for g in contact['geometries']})
            self.assertEqual({'robot','wall'},{g['root'] for g in contact['geometries']})
        wrist = geom_detail(model,data,model.geom('wrist_geom').id)
        np.testing.assert_allclose([.12,-.08,-.08],wrist['aabb']['low'],atol=1e-12)
        self.assertEqual([],contact_details(model,data,[['unrelated','wall']])['contacts'])


if __name__=='__main__':
    unittest.main()

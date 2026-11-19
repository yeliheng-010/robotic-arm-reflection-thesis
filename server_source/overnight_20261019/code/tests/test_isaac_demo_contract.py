import unittest
from pathlib import Path

from isaac_embodied_demo.layout import outside_room, unexpected_overlaps, validate_layout
from isaac_embodied_demo.task_config import (
    DYNAMIC_CORRIDOR_OBSTACLES,
    NAVIGATION_POSES,
    OBJECT_TASKS,
)


ROOT = Path(__file__).resolve().parents[1]


class IsaacDemoContractTests(unittest.TestCase):
    def test_measured_furniture_layout_has_no_overlap_or_wall_penetration(self):
        self.assertEqual(unexpected_overlaps(), [])
        self.assertEqual(outside_room(), [])
        validate_layout()

    def test_task_controller_never_teleports_or_makes_the_mug_kinematic(self):
        source = (ROOT / "isaac_embodied_demo" / "controller.py").read_text()
        self.assertNotIn("set_world_pose", source)
        self.assertNotIn("KinematicEnabled", source)
        self.assertNotIn("FilteredPairsAPI", source)
        self.assertNotIn("_sync_held_mug", source)

    def test_home_mission_has_three_objects_four_zones_and_two_routes(self):
        self.assertEqual(
            [task.object_id for task in OBJECT_TASKS],
            ["cup", "medicine_box", "toy"],
        )
        self.assertEqual(
            {task.object_id: task.target_zone for task in OBJECT_TASKS},
            {
                "cup": "care_station",
                "medicine_box": "care_station",
                "toy": "storage_bin",
            },
        )
        self.assertTrue(OBJECT_TASKS[0].keep_upright)
        self.assertTrue(
            {"living_table", "care_station", "storage_bin", "buffer_tray"}
            <= set(NAVIGATION_POSES)
        )
        self.assertEqual(
            set(DYNAMIC_CORRIDOR_OBSTACLES),
            {"corridor_low", "corridor_high"},
        )

    def test_mobile_navigation_and_failure_memory_are_part_of_controller(self):
        controller = (ROOT / "isaac_embodied_demo" / "controller.py").read_text()
        for contract in (
            "AStarNavigator",
            "set_mobile_base_pose",
            "inject_path_blocked",
            "inject_object_moved",
            "inject_grasp_drop",
            "inject_target_occupied",
            "mission_complete:home_care_and_tidy",
        ):
            self.assertIn(contract, controller)

    def test_native_view_makes_the_multi_goal_plan_and_replanning_visible(self):
        scene = (ROOT / "isaac_embodied_demo" / "scene.py").read_text()
        ui = (ROOT / "isaac_embodied_demo" / "ui.py").read_text()
        main = (ROOT / "isaac_embodied_demo" / "main.py").read_text()
        self.assertIn("ActiveAStarPath", scene)
        self.assertIn("UsdGeom.BasisCurves", scene)
        self.assertIn("Household Mission (not a single-cup demo)", ui)
        self.assertIn("Cup -> care station (upright)", ui)
        self.assertIn("dock_in(viewport, ui.DockPosition.RIGHT)", ui)
        self.assertIn('"--showcase"', main)

    def test_grasp_requires_contact_and_authors_a_real_physx_joint(self):
        controller = (ROOT / "isaac_embodied_demo" / "controller.py").read_text()
        scene = (ROOT / "isaac_embodied_demo" / "scene.py").read_text()
        self.assertIn("get_rigid_body_raw_data", controller)
        self.assertIn("UsdPhysics.FixedJoint.Define", controller)
        self.assertIn("PhysxContactReportAPI.Apply", scene)
        self.assertIn("support_contact", controller)

    def test_scene_does_not_nest_the_complete_simple_room_environment(self):
        scene = (ROOT / "isaac_embodied_demo" / "scene.py").read_text()
        assets = (ROOT / "isaac_embodied_demo" / "assets.py").read_text()
        self.assertNotIn("Simple_Room", scene)
        self.assertNotIn('"room": AssetSpec', assets)
        self.assertIn("_make_architectural_shell", scene)


if __name__ == "__main__":
    unittest.main()

import os
import unittest

os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/future-embodied-tests-mpl")

from future_embodied_demo.engine import DemoEngine
from future_embodied_demo.models import SkillRequest
from future_embodied_demo.native_viewer import render_native_hud
from future_embodied_demo.simulator import MobileHomeSimulator, NAVIGATION_GOALS


class FutureEmbodiedSimulatorTests(unittest.TestCase):
    def setUp(self):
        self.simulator = MobileHomeSimulator(realtime=False)

    def tearDown(self):
        self.simulator.close()

    def test_home_scene_exposes_mobile_body_and_two_functional_zones(self):
        snapshot = self.simulator.observe()
        self.assertEqual(snapshot.entities["cup"].zone, "living_table")
        self.assertEqual(snapshot.entities["toy"].zone, "living_table")
        self.assertIsNone(snapshot.robot.holding)
        self.assertIn("care_station", NAVIGATION_GOALS)
        self.assertIn("storage_bin", NAVIGATION_GOALS)

    def test_blocked_upper_corridor_uses_lower_route(self):
        self.simulator._set_base_pose((*NAVIGATION_GOALS["living_table"][:2], 0.0))
        self.simulator.inject_event("path_blocked", target="corridor_high")
        result = self.simulator.execute(SkillRequest("navigate", "care_station"))
        self.assertTrue(result.success, result.message)
        path = result.observed_effects["path"]
        self.assertLess(min(point[1] for point in path), 1.5)

    def test_nominal_task_closes_the_physical_state_loop(self):
        engine = DemoEngine(simulator=self.simulator, memory_path=":memory:")
        engine.start("把水杯放到照护区并保持直立", background=False)
        state = engine.state()
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["world"]["entities"]["cup"]["zone"], "care_station")
        self.assertIn("cup", state["completed"])
        engine.memory.close()

    def test_occupied_target_is_cleared_before_original_goal(self):
        self.simulator.inject_event("target_occupied", target="care_station")
        engine = DemoEngine(simulator=self.simulator, memory_path=":memory:")
        engine.start("把水杯放到照护区", background=False)
        state = engine.state()
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["world"]["entities"]["target_blocker"]["zone"], "buffer_tray")
        self.assertEqual(state["world"]["entities"]["cup"]["zone"], "care_station")
        engine.memory.close()

    def test_soft_reset_restores_scene_without_replacing_mujoco_objects(self):
        model = self.simulator.mj_model
        data = self.simulator.mj_data
        self.simulator.inject_event("object_moved", target="cup")
        self.simulator.inject_event("target_occupied", target="care_station")

        snapshot = self.simulator.soft_reset()

        self.assertIs(self.simulator.mj_model, model)
        self.assertIs(self.simulator.mj_data, data)
        self.assertEqual(snapshot.entities["cup"].zone, "living_table")
        self.assertEqual(snapshot.entities["toy"].zone, "living_table")
        self.assertNotIn("care_station", snapshot.occupied_targets)
        self.assertIsNone(snapshot.robot.holding)

    def test_native_hud_is_a_nonempty_rgb_image(self):
        engine = DemoEngine(simulator=self.simulator, memory_path=":memory:")
        try:
            state = engine.state()
            panel = render_native_hud(state, width=430, height=760, notice="仿真已就绪")
            self.assertEqual(panel.shape, (760, 430, 3))
            self.assertEqual(panel.dtype.name, "uint8")
            self.assertGreater(int(panel.max()), int(panel.min()))
            self.assertGreater(int((panel != panel[0, 0]).any(axis=2).sum()), 100)
        finally:
            engine.memory.close()


if __name__ == "__main__":
    unittest.main()

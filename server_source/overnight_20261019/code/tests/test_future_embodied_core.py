import tempfile
import unittest
from pathlib import Path

from future_embodied_demo.cognitive import FutureAIEmulator
from future_embodied_demo.language import UnsupportedInstruction, parse_instruction
from future_embodied_demo.memory import MemoryStore
from future_embodied_demo.models import (
    CapabilitySpec,
    MemoryEpisode,
    RobotState,
    WorldEntity,
    WorldSnapshot,
)
from future_embodied_demo.registry import (
    EmbodiedAgent,
    default_mobile_manipulator_registry,
)
from future_embodied_demo.world import WorldModel


def sample_world():
    return WorldSnapshot(
        version=1,
        entities={
            "cup": WorldEntity("cup", "household_object", (1.3, 0.7, 0.74), "living_table"),
            "medicine_box": WorldEntity(
                "medicine_box", "household_object", (1.7, 0.9, 0.71), "living_table"
            ),
            "toy": WorldEntity("toy", "household_object", (1.9, 0.7, 0.71), "living_table"),
        },
        robot=RobotState(0.8, 2.0),
    )


class FutureEmbodiedCoreTests(unittest.TestCase):
    def test_controlled_chinese_maps_to_typed_goal(self):
        goal = parse_instruction(
            "把客厅桌上的水杯和药盒送到照护区，把玩具放进收纳箱，并保持水杯直立"
        )
        self.assertEqual(
            [(item.object_id, item.target_zone) for item in goal.items],
            [
                ("cup", "care_station"),
                ("medicine_box", "care_station"),
                ("toy", "storage_bin"),
            ],
        )
        self.assertTrue(goal.items[0].constraints["upright"])

    def test_unsupported_command_is_rejected_instead_of_invented(self):
        with self.assertRaises(UnsupportedInstruction):
            parse_instruction("帮我写一首诗")

    def test_memory_persists_and_is_retrievable_by_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            first = MemoryStore(path)
            first.record(
                MemoryEpisode(
                    "grasp_lost:cup",
                    {"surface": "slippery"},
                    {"grasp_profile": "secure"},
                    "repair_planned",
                )
            )
            first.close()
            second = MemoryStore(path)
            episodes = second.find("grasp_lost:cup")
            self.assertEqual(len(episodes), 1)
            self.assertEqual(episodes[0].repair["grasp_profile"], "secure")
            second.close()

    def test_memory_changes_grasp_and_route_strategy(self):
        memory = MemoryStore(":memory:")
        memory.record(
            MemoryEpisode(
                "grasp_lost:cup", {}, {"grasp_profile": "secure"}, "repair_planned"
            )
        )
        memory.record(
            MemoryEpisode(
                "path_blocked:care_station",
                {"blocked_corridors": ["corridor_high"]},
                {"avoid_new_obstacle": True},
                "repair_planned",
            )
        )
        cognitive = FutureAIEmulator(default_mobile_manipulator_registry(), memory)
        plan = cognitive.plan(parse_instruction("把水杯送到照护区"), sample_world())
        grasp = next(step for step in plan if step.skill == "grasp")
        transport = next(
            step
            for step in plan
            if step.skill == "navigate" and step.params.get("carrying") == "cup"
        )
        self.assertEqual(grasp.params["profile"], "secure")
        self.assertEqual(transport.params["avoid_corridors"], ["corridor_high"])
        self.assertIn("历史", transport.explanation)
        memory.close()

    def test_new_embodied_tool_registers_without_core_changes(self):
        registry = default_mobile_manipulator_registry()
        camera = EmbodiedAgent("ceiling_camera", "独立房间摄像头")
        camera.add_capability(
            CapabilitySpec("track", "ceiling_camera", "持续跟踪移动物体")
        )
        registry.register(camera)
        self.assertEqual(registry.providers_for("track")[0].agent_id, "ceiling_camera")

    def test_occupied_destination_stages_held_object_before_clearing(self):
        memory = MemoryStore(":memory:")
        cognitive = FutureAIEmulator(default_mobile_manipulator_registry(), memory)
        world = sample_world()
        world.robot.holding = "cup"
        world.occupied_targets = ("care_station",)
        plan = cognitive.plan(parse_instruction("把水杯送到照护区"), world)
        self.assertEqual([step.skill for step in plan], ["navigate", "dock", "place", "verify"])
        self.assertEqual(plan[0].target, "buffer_tray")
        self.assertIn("暂存", plan[0].explanation)
        memory.close()

    def test_world_model_reports_semantic_changes(self):
        model = WorldModel()
        before = sample_world()
        model.update(before)
        after = sample_world()
        after.version = 2
        after.entities["cup"].position = (2.0, 1.0, 0.74)
        after.entities["cup"].zone = "floor"
        changes = model.update(after)
        kinds = {change.kind for change in changes}
        self.assertIn("entity_moved", kinds)
        self.assertIn("entity_zone_changed", kinds)


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from reflection.__main__ import main
from reflection.engine import FeedbackEngine
from reflection.language import resolve_task


class LanguageTaskTests(unittest.TestCase):
    def test_language_selects_actual_non_default_targets(self):
        examples = (
            ("请把绿色圆柱放进红色箱子。", "GreenCylinder", "RedBin"),
            ("将橙色小球放到黄色托盘上", "OrangeSphere", "SortingTray"),
            ("Please put the purple capsule into the blue box.", "PurpleCapsule", "BlueBin"),
        )
        for instruction, source, destination in examples:
            with self.subTest(instruction=instruction):
                task = resolve_task(instruction)
                self.assertEqual((task.source, task.destination), (source, destination))
                self.assertEqual(task.parser, "rule")

    def test_unclear_or_unsupported_commands_do_not_become_default_tasks(self):
        for instruction in ("", "不要把红色方块放进蓝色箱子", "把红色方块和绿色圆柱放进蓝色箱子",
                            "把红色方块放进蓝色箱子，然后回到桌子", "把红色方块放在蓝色箱子上面",
                            "把杯子放进蓝色箱子", "把红色方块放过去"):
            with self.subTest(instruction=instruction), self.assertRaises(ValueError):
                resolve_task(instruction)

    def test_explicit_targets_preserve_defaults_and_reject_language_conflicts(self):
        task = resolve_task()
        self.assertEqual((task.source, task.destination), ("RedBlock", "BlueBin"))
        self.assertEqual(resolve_task(source="GreenCylinder").source, "GreenCylinder")
        with self.assertRaises(ValueError):
            resolve_task("把绿色圆柱放进红色箱子", source="RedBlock")

    def test_llm_resolution_validates_scene_targets_and_supported_boolean(self):
        client = Mock()
        client.ask_json.return_value = {"supported": True, "source": "GreenCylinder", "destination": "BlueBin"}
        task = resolve_task("把那个绿色的圆柱形物体收到蓝箱里", client=client)
        self.assertEqual((task.source, task.destination, task.parser), ("GreenCylinder", "BlueBin", "llm"))
        for value in ({"supported": "true", "source": "RedBlock", "destination": "BlueBin"},
                      {"supported": True, "source": ["RedBlock"], "destination": "BlueBin"},
                      {"supported": True, "source": "Cup", "destination": "BlueBin"},
                      {"supported": False, "reason": "Unsupported stacking"}):
            client.ask_json.return_value = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_task("用户任务", parser="llm", client=client)

    def _engine(self):
        engine = FeedbackEngine()
        engine._attempt = Mock(return_value=({"accepted": True, "physical_success": True}, None))
        return engine

    def test_engine_executes_resolved_targets_and_logs_interpretation(self):
        engine = self._engine()
        with tempfile.TemporaryDirectory() as directory:
            result = engine.run(instruction="把绿色圆柱放进红色箱子", method="baseline", fault="none", output=directory)
            self.assertEqual(engine._attempt.call_args.args[:2], ("GreenCylinder", "RedBin"))
            logged = json.loads((Path(directory) / "result.json").read_text())
            self.assertEqual(logged["task_resolution"]["parser"], "rule")
            self.assertEqual(result["destination"], "RedBin")
            engine._attempt.reset_mock()
            with self.assertRaises(ValueError):
                engine.run(instruction="不要搬运红色方块", method="baseline", output=directory)
            engine._attempt.assert_not_called()

    def test_interactive_input_continues_after_invalid_task_and_preserves_existing_logs(self):
        engine = self._engine()
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "task_001"
            existing.mkdir()
            marker = existing / "result.json"
            marker.write_text("existing log")
            with patch("sys.argv", ["reflection", "--interactive", "--headless", "--method", "baseline", "--fault", "none",
                                    "--output", directory, "--memory", str(Path(directory) / "memory.sqlite3")]), \
                    patch("reflection.__main__.build_engine", return_value=engine), \
                    patch("builtins.input", side_effect=["不要搬运红色方块", "把绿色圆柱放进红色箱子", "exit"]):
                main()
            self.assertEqual(marker.read_text(), "existing log")
            self.assertEqual(engine._attempt.call_count, 1)
            results = [p for p in Path(directory).glob("task_*/result.json") if p != marker]
            self.assertEqual(len(results), 1)
            self.assertEqual(json.loads(results[0].read_text())["source"], "GreenCylinder")

    def test_interactive_default_prepares_scene_before_input_and_closes_on_exit(self):
        engine = Mock()
        engine.client = None

        def input_after_scene(prompt):
            engine.prepare_scene.assert_called_once_with("none")
            return "exit"

        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv", ["reflection", "--interactive", "--fault", "none",
                                    "--memory", str(Path(directory) / "memory.sqlite3")]), \
                    patch.dict("os.environ", {"DISPLAY": ":0"}), \
                    patch("reflection.__main__.build_engine", return_value=engine) as build, \
                    patch("builtins.input", side_effect=input_after_scene):
                main()
            self.assertTrue(build.call_args.args[0].viewer)
            engine.run.assert_not_called()
            engine.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

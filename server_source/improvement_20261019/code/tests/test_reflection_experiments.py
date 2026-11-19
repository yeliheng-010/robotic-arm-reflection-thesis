import json
from pathlib import Path
import tempfile
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import mujoco
import numpy as np
import spatialmath as sm

from experiments.run_benchmark import main, service_failed, summarize
from experiments.run_suite import make_plan, run_stage, stage_command
from reflection.errors import ErrorReport, ErrorType
from reflection.fault_injection import Fault
from reflection.reflector import Parameters, RuleReflector


def result_for(method="reflection_memory", fault="collision", seed=42):
    return {"method": method, "source": "RedBlock", "destination": "BlueBin", "fault": fault,
            "seed": seed, "success": True, "attempts": 1, "elapsed_s": 1.0, "memory_hit": False,
            "perception": "simulation", "segmentation": "simulation", "reflector": "RuleReflector",
            "records": [{"attempt": 1, "physical_success": True, "accepted": True,
                         "parameters": {}, "last_stage": "placement", "error": None, "visual": None}]}


class ExperimentTests(unittest.TestCase):
    def test_protocol_sizes_and_equal_attempt_budgets(self):
        for profile, expected in (("smoke", 24), ("pilot", 336), ("thesis", 1120)):
            plan = make_plan(profile)
            self.assertEqual(sum(s["tasks"] for s in plan), expected)
            self.assertTrue(all(s["max_attempts"] == 3 for s in plan))
        self.assertEqual(sum(s["tasks"] for s in make_plan("thesis", ["mechanism"])), 560)
        with self.assertRaises(ValueError):
            make_plan("smoke", ["integrated"])

    def test_filtered_suite_has_30_paired_tasks_and_rejects_invalid_selections(self):
        selection = {"methods": ["retry", "reflection", "reflection_memory"],
                     "sources": ["RedBlock"],
                     "faults": ["none", "calibration", "collision", "slip", "placement"]}
        stage = make_plan("pilot", ["mechanism"], episodes=2, **selection)[0]
        self.assertEqual(stage["tasks"], 30)
        self.assertEqual(stage["reflector"], "llm")
        self.assertEqual(stage["destination"], "BlueBin")
        for key, values in selection.items():
            self.assertEqual(stage[key], values)
        red_bin = make_plan("pilot", ["mechanism"], destination="RedBin")[0]
        self.assertEqual(red_bin["destination"], "RedBin")
        command = stage_command(red_bin, Path("/tmp/reflection-red-bin"))
        self.assertEqual(command[command.index("--destination") + 1], "RedBin")
        with self.assertRaises(ValueError):
            make_plan("pilot", methods=["retry", "retry"])
        with self.assertRaises(ValueError):
            make_plan("smoke", faults=["none"])
        with self.assertRaises(ValueError):
            make_plan("pilot", destination="Unknown")

    def test_suite_interrupt_waits_for_child_to_exit(self):
        children = []
        original = subprocess.Popen

        def track_child(*args, **kwargs):
            process = original(*args, **kwargs)
            children.append(process)
            return process

        with tempfile.TemporaryDirectory() as directory:
            with patch("experiments.run_suite.subprocess.Popen", side_effect=track_child), \
                    patch("builtins.print", side_effect=KeyboardInterrupt):
                code = run_stage([sys.executable, "-u", "-c", "import time; print('ready'); time.sleep(30)"],
                                 Path(directory) / "stage.log")
            self.assertEqual(code, 130)
            self.assertIsNotNone(children[0].poll())

    def test_resume_does_not_repeat_finished_episode_or_leak_interrupted_memory(self):
        calls = []
        interrupted = False
        report = ErrorReport(ErrorType.COLLISION, "hit")
        correction = RuleReflector().reflect(report, Parameters())

        def factory(args, memory):
            def run(**kwargs):
                nonlocal interrupted
                seed = kwargs["seed"]
                calls.append(seed)
                if seed == 43:
                    self.assertIsNotNone(memory.recall("valid"))
                    self.assertIsNone(memory.recall("interrupted"))
                    if not interrupted:
                        interrupted = True
                        memory.remember("interrupted", [report], Parameters().updated(correction.changes), [correction])
                        raise KeyboardInterrupt
                else:
                    memory.remember("valid", [report], Parameters().updated(correction.changes), [correction])
                result = result_for(seed=seed)
                directory = kwargs["output"]
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "result.json").write_text(json.dumps(result))
                return result
            return SimpleNamespace(run=run, close=Mock(), client=None)

        with tempfile.TemporaryDirectory() as directory:
            argv = ["--methods", "reflection_memory", "--faults", "collision", "--episodes", "2",
                    "--headless", "--output", directory]
            with patch("experiments.run_benchmark.build_engine", side_effect=factory), \
                    patch("experiments.run_benchmark.plot_summary"):
                self.assertEqual(main(argv), 130)
                self.assertEqual(main(argv+["--resume"]), 0)
                with self.assertRaises(SystemExit):
                    main(argv+["--resume", "--seed", "99"])
            self.assertEqual(calls, [42, 43, 43])
            status = json.loads((Path(directory) / "status.json").read_text())
            self.assertTrue(status["complete"])
            self.assertEqual(status["completed"], 2)

    def test_model_outage_is_preserved_but_excluded_and_resume_restores_memory(self):
        outage = True
        report = ErrorReport(ErrorType.COLLISION, "hit")
        correction = RuleReflector().reflect(report, Parameters())

        def factory(args, memory):
            def run(**kwargs):
                nonlocal outage
                self.assertIsNone(memory.recall("outage"))
                result = result_for()
                if outage:
                    outage = False
                    result["records"][0]["visual"] = {"success": None, "status": "api_error"}
                    memory.remember("outage", [report], Parameters().updated(correction.changes), [correction])
                (kwargs["output"] / "result.json").write_text(json.dumps(result))
                return result
            return SimpleNamespace(run=run, close=Mock(), client=None)

        with tempfile.TemporaryDirectory() as directory:
            argv = ["--methods", "reflection_memory", "--faults", "collision", "--episodes", "1",
                    "--stop-on-api-error", "--headless", "--output", directory]
            with patch("experiments.run_benchmark.build_engine", side_effect=factory), \
                    patch("experiments.run_benchmark.plot_summary"):
                self.assertEqual(main(argv), 1)
                self.assertTrue((Path(directory) / "reflection_memory/RedBlock/collision/episode_1/service_error.json").exists())
                self.assertEqual(json.loads((Path(directory) / "status.json").read_text())["completed"], 0)
                self.assertEqual(main(argv+["--resume"]), 0)

    def test_physical_success_and_model_acceptance_are_separate(self):
        row = {"method": "reflection", "memory_phase": "cold", "success": False,
               "physical_success": True, "first_attempt_success": False, "initial_failure": True,
               "recovered": True, "attempts": 2, "elapsed_s": 3, "memory_hit": False}
        summary = summarize([row])[0]
        self.assertEqual(summary["success_rate"], 0)
        self.assertEqual(summary["physical_success_rate"], 1)
        self.assertEqual(summary["recovery_rate"], 1)
        result = result_for()
        result["records"][0]["visual"] = {"status": "invalid_response", "success": None}
        self.assertFalse(service_failed(result))

    def test_jitter_is_paired_and_changes_only_requested_object(self):
        xml = '<mujoco><worldbody><body name="RedBlock" pos="1 2 3"/><body name="Other" pos="4 5 6"/></worldbody></mujoco>'
        positions = []
        for seed in (42, 42, 43):
            spec = mujoco.MjSpec.from_string(xml)
            Fault("none", "RedBlock", seed, 0.008).model_editor(spec)
            positions.append(np.array(spec.body("RedBlock").pos))
            np.testing.assert_array_equal(spec.body("Other").pos, [4, 5, 6])
        np.testing.assert_array_equal(positions[0], positions[1])
        self.assertFalse(np.array_equal(positions[0], positions[2]))
        self.assertLessEqual(np.abs(positions[0]-[1, 2, 3]).max(), 0.008)

    def test_reset_restores_physics_and_robot_without_replacing_viewer(self):
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
        model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><body pos="0 0 1"><freejoint/><geom size=".1"/></body></worldbody></mujoco>')
        data = mujoco.MjData(model)
        state_spec = mujoco.mjtState.mjSTATE_INTEGRATION
        initial = np.empty(mujoco.mj_stateSize(model, state_spec))
        mujoco.mj_getState(model, data, initial, state_spec)
        viewer = Mock()
        env = SimpleNamespace(mj_model=model, mj_data=data, _state_spec=state_spec,
                              _initial_state=initial, _initial_robot_q=np.zeros(6),
                              robot=Mock(), T0=sm.SE3(), mj_viewer=viewer)
        for _ in range(100):
            mujoco.mj_step(model, data)
        UR5GraspEnv.reset_state(env)
        restored = np.empty_like(initial)
        mujoco.mj_getState(model, data, restored, state_spec)
        np.testing.assert_array_equal(initial, restored)
        self.assertIs(env.mj_viewer, viewer)
        viewer.sync.assert_called_once()

    def test_temporary_segmentation_cleanup_preserves_reused_rgbd_renderer(self):
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
        from reflection.sim_sensing import SegmentationRenderer
        env = UR5GraspEnv(headless=True)
        try:
            env.reset()
            for _ in range(500):
                env.step()
            initial = env.render()
            segmentation = SegmentationRenderer(env.mj_model, env.height, env.width)
            try:
                segmentation.root_map(env.mj_data)
                env.render()  # Bind the depth renderer before segmentation cleanup.
            finally:
                segmentation.close()
            after = env.render()
            np.testing.assert_allclose(initial["depth"], after["depth"], atol=1e-6)
            # EGL 光栅化在同一渲染器连续两帧之间也有约 0.02% 像素的 RGB 抖动，
            # 因此只要求绝大多数像素一致；渲染器被破坏时会整帧错误。
            mismatched = np.any(initial["img"] != after["img"], axis=-1).mean()
            self.assertLess(mismatched, 0.005)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()

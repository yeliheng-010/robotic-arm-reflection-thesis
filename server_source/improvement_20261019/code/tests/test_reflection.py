import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import mujoco
import numpy as np

from reflection.errors import ErrorReport, ErrorType, TaskAbort
from reflection.engine import canonical_plan
from reflection.memory import ExperienceMemory
from reflection.monitors import evaluate_placement, validate_grounding, validate_mask, validate_plan, verify_visual
from reflection.reflector import LLMReflector, Parameters, RuleReflector


class ReflectionTests(unittest.TestCase):
    def test_plan_cannot_release_before_grasp_or_change_requested_object(self):
        plan = canonical_plan("RedBlock", "BlueBin", (1, 1), (2, 2))
        self.assertEqual(len(validate_plan(plan, "RedBlock", "BlueBin", lambda n: n)), 5)
        plan["action_components"][0]["component"][0] = "GreenCylinder"
        with self.assertRaises(TaskAbort) as caught:
            validate_plan(plan, "RedBlock", "BlueBin", lambda n: n)
        self.assertEqual(caught.exception.report.error_type, ErrorType.PLAN_WRONG_OBJECT)
        plan["action_components"].reverse()
        with self.assertRaises(TaskAbort) as caught:
            validate_plan(plan, "RedBlock", "BlueBin", lambda n: n)
        self.assertEqual(caught.exception.report.error_type, ErrorType.PLAN_SEQUENCE_INVALID)

    def test_malformed_model_target_is_reported_before_name_resolution(self):
        def resolve(name):
            self.fail("Malformed target must not reach the scene resolver")

        for component in ((["RedBlock"], "center"), (None, "center"), ("RedBlock", {}), ("", "center")):
            with self.subTest(component=component):
                plan = canonical_plan("RedBlock", "BlueBin", (1, 1), (2, 2))
                plan["action_components"][0]["component"] = list(component)
                with self.assertRaises(TaskAbort) as caught:
                    validate_plan(plan, "RedBlock", "BlueBin", resolve)
                self.assertEqual(caught.exception.report.error_type, ErrorType.PLAN_PARSE_ERROR)

    def test_grounding_rejects_background_invalid_depth_and_out_of_bounds(self):
        root = np.full((30, 30), -1)
        root[10:20, 10:20] = 3
        depth = np.ones((30, 30))
        for pixel, kind in [((-2, 0), ErrorType.GROUNDING_OUT_OF_IMAGE),
                            ((0, 0), ErrorType.GROUNDING_OFF_TARGET)]:
            with self.assertRaises(TaskAbort) as caught:
                validate_grounding(pixel, depth, root, 3)
            self.assertEqual(caught.exception.report.error_type, kind)
        depth[15, 15] = np.nan
        with self.assertRaises(TaskAbort) as caught:
            validate_grounding((15, 15), depth, root, 3)
        self.assertEqual(caught.exception.report.error_type, ErrorType.DEPTH_INVALID)
        with self.assertRaises(TaskAbort):
            validate_mask(np.ones((30, 30)), root, 3)

    def test_model_corrections_are_bounded_and_never_coerce_invalid_types(self):
        for changes in ({"lift_height": 4}, {"grasp_offset": [0, float("nan"), 0]},
                        {"replan": "false"}, {"candidate_index": True}, {"execute": "anything"}):
            with self.assertRaises(ValueError):
                Parameters().updated(changes)
        class Client:
            def ask_json(self, *args, **kwargs):
                return {"cause": "collision", "changes": {"lift_height": 100}}
        with self.assertRaises(ValueError):
            LLMReflector(Client()).reflect(ErrorReport(ErrorType.COLLISION, "hit"), Parameters())

    def test_memory_only_remembers_validated_experience_and_isolates_contexts(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = ExperienceMemory(Path(directory) / "memory.sqlite3")
            report = ErrorReport(ErrorType.COLLISION, "divider hit")
            correction = RuleReflector().reflect(report, Parameters())
            self.assertIsNone(memory.recall("setup"))
            memory.remember("setup", [report], Parameters().updated(correction.changes), [correction])
            self.assertIsNone(memory.recall("other-setup"))
            recalled = memory.recall("setup")
            self.assertEqual(recalled["parameters"]["lift_height"], 0.45)
            memory.feedback("setup", recalled["signature"], False)
            self.assertIsNone(memory.recall("setup"))
            memory.close()

    def test_rules_compensate_observed_residual_instead_of_fault_label(self):
        report = ErrorReport(ErrorType.EMPTY_GRASP, "missed", {"grasp_residual_xy": [0, -0.045]})
        correction = RuleReflector().reflect(report, Parameters())
        self.assertEqual(correction.changes["grasp_offset"], [0, 0.045, 0])

    def test_visual_verdict_requires_a_real_boolean_or_unknown(self):
        class Client:
            def ask_json(self, *args, **kwargs):
                return {"success": "false", "reason": "not in container"}
        with self.assertRaises(ValueError):
            verify_visual(Client(), "before", "after", "task")

    def test_physical_evaluator_rejects_hovering_and_partial_containment(self):
        model = mujoco.MjModel.from_xml_string('''<mujoco><worldbody>
            <body name="BlueBin"><geom name="blue_bin_floor" type="box" size="0.14 0.12 0.01" pos="0 0 0.01"/>
            <geom name="blue_bin_left_wall" type="box" size="0.012 0.132 0.08" pos="-0.14 0 0.08"/></body>
            <body name="RedBlock" pos="0 0 0.06"><freejoint/><geom type="box" size="0.038 0.031 0.038"/></body>
            </worldbody></mujoco>''')
        data = mujoco.MjData(model)
        env = SimpleNamespace(mj_model=model, mj_data=data)
        for _ in range(1000):
            mujoco.mj_step(model, data)
        success, _, _ = evaluate_placement(env, "RedBlock", "BlueBin", np.array([1., 0, 0, 0]))
        self.assertTrue(success)
        data.qpos[2] = 0.4
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)
        success, evidence, _ = evaluate_placement(env, "RedBlock", "BlueBin", np.array([1., 0, 0, 0]))
        self.assertFalse(success)
        self.assertFalse(evidence["supported"])
        data.qpos[:3] = [0.12, 0, 0.058]
        mujoco.mj_forward(model, data)
        success, evidence, _ = evaluate_placement(env, "RedBlock", "BlueBin", np.array([1., 0, 0, 0]))
        self.assertFalse(success)
        self.assertFalse(evidence["inside_xy"])


if __name__ == "__main__":
    unittest.main()

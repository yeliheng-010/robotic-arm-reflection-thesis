"""A bounded feedback loop over the existing physical GraspFlow."""
import json
from pathlib import Path
import time

import cv2
import numpy as np
import spatialmath as sm

from .errors import ErrorReport, ErrorType, TaskAbort
from .fault_injection import Fault
from .language import LABELS, resolve_task
from .llm import LLMServiceError
from .monitors import (ExecutionMonitor, evaluate_placement, validate_grounding,
                       validate_mask, validate_plan, verify_visual)
from .reflector import Parameters, stable_error
from .sim_sensing import SegmentationRenderer, project_to_pixel


METHODS = ("baseline", "retry", "reflection", "reflection_memory")


def canonical_plan(source, destination, pixel, target_pixel):
    return {"action_components": [
        {"action": "move_to_grasp_pose", "component": [source, "center"], "args": {"pixel": list(pixel)}},
        {"action": "close_gripper", "component": [source, "center"]},
        {"action": "move_to_point", "component": [destination, "center"], "args": {"pixel": list(target_pixel)}},
        {"action": "open_gripper"}, {"action": "back_to_zero"}]}


class FeedbackEngine:
    def __init__(self, *, reflector=None, memory=None, client=None, perception="simulation",
                 segmentation="simulation", grasp_backend="geometric", headless=True, max_attempts=3,
                 visual_verify=False, task_parser="auto", scene_jitter=0.0):
        if perception not in {"simulation", "vlm"} or segmentation not in {"simulation", "sam"}:
            raise ValueError("Unknown perception/segmentation mode")
        self.reflector, self.memory, self.client = reflector, memory, client
        self.perception, self.segmentation, self.grasp_backend = perception, segmentation, grasp_backend
        self.headless, self.max_attempts = headless, max_attempts
        self.visual_verify = visual_verify
        self.task_parser = task_parser
        Fault(position_jitter=scene_jitter)
        self.scene_jitter = scene_jitter
        self._preview_env = None
        self._preview_fault = None
        if perception == "vlm" and client is None:
            raise ValueError("VLM perception requires a client")

    def prepare_scene(self, fault="none"):
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv

        if self._preview_env is not None and self._preview_fault != fault:
            self.close()
        if self._preview_env is None:
            env = UR5GraspEnv(headless=self.headless, model_editor=Fault(fault).model_editor)
            self._preview_env, self._preview_fault = env, fault
            env.reset()
            if env.mj_viewer is not None:
                env.mj_viewer.cam.lookat[:] = [1.10, 0.60, 1.15]
                env.mj_viewer.cam.distance = 2.6
        else:
            self._preview_env.reset_state()
        for _ in range(500):
            self._preview_env.step()

    def close(self):
        if self._preview_env is not None:
            self._preview_env.close()
            self._preview_env = None
            self._preview_fault = None

    def _resolve(self, env, name):
        # 模型现在用自由描述（如 "red box"、"blue container"）命名物体，
        # 复用 main_vlm 的开放词汇映射，再补充本场景的中英文别名。
        from .language import DESTINATION_ALIASES, SOURCE_ALIASES

        text = " ".join(str(name).casefold().replace("_", " ").split())
        for body, words in {**SOURCE_ALIASES, **DESTINATION_ALIASES}.items():
            if text in {w.casefold() for w in words}:
                return body
        extra = {"red box": "RedBin", "red container": "RedBin", "blue box": "BlueBin",
                 "blue container": "BlueBin", "yellow tray": "SortingTray", "tray": "SortingTray",
                 "purple pill": "PurpleCapsule", "orange ball": "OrangeSphere", "green can": "GreenCylinder"}
        if text in extra:
            return extra[text]
        from main_vlm import _resolve_scene_body_id

        body_id = _resolve_scene_body_id(env, text)
        return env.mj_model.body(body_id).name if body_id >= 0 else None

    def _plan(self, env, before, instruction, source, destination, params, history):
        if self.perception == "simulation":
            return canonical_plan(source, destination,
                                  project_to_pixel(env, env.mj_data.body(source).xpos),
                                  project_to_pixel(env, env.mj_data.body(destination).xpos))
        # 只给自然语言指令与场景图像，不告诉模型应操作哪个物体：
        # 物体选择与定位错误（例如把"红色方块"定位到红色箱子）会自然出现，
        # 再由 validate_plan / validate_grounding 检测，交给反思模块处理。
        history_text = json.dumps([{**item, "error": stable_error(item["error"])} for item in history],
                                  ensure_ascii=False)
        prompt = (
            "You are the task planner of a UR5e arm with a parallel gripper. Read the user's "
            "instruction, look at the scene image, decide which object to pick and which container "
            "to place it in, and locate both in the image.\n"
            "Return JSON {\"action_components\":[...]} with exactly five actions in this order: "
            "move_to_grasp_pose, close_gripper, move_to_point, open_gripper, back_to_zero. "
            "Each action is {\"action\":..., \"component\":[object, part], \"args\":{...}}. "
            "move_to_grasp_pose and close_gripper refer to the object to pick; move_to_point refers "
            "to the container. Describe objects by colour and shape in English (e.g. \"yellow duck\", "
            "\"red bin\"). move_to_grasp_pose and move_to_point must include args.pixel=[u,v], the "
            "visible centre of that object on a normalized 0..1000 image grid. "
            "Do not include motion parameters in args.\n"
            f"Instruction: {instruction}\n"
            f"Earlier failed attempts of this task (errors and corrections): {history_text}\n"
            f"Replan requested: {params.replan}; reground requested: {params.reground}."
        )
        plan = self.client.ask_json(prompt, images=[str(before)], max_tokens=2000, cache_tag="plan-ground-v3")
        components = plan.get("action_components", [])
        if isinstance(components, list):
            for action in components:
                if not isinstance(action, dict) or not isinstance(action.get("args"), dict):
                    continue
                pixel = action["args"].get("pixel")
                if (isinstance(pixel, list) and len(pixel) == 2 and
                        all(type(v) in (int, float) and np.isfinite(v) for v in pixel)):
                    action["args"]["pixel"] = [round(pixel[0] * env.width/1000), round(pixel[1] * env.height/1000)]
        return plan

    def _attempt(self, source, destination, instruction, fault, attempt, params, directory, history):
        from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
        from grasp_process import GraspFlow, run_grasp_inference

        directory.mkdir(parents=True, exist_ok=True)
        before, after = directory / "before.png", directory / "after.png"
        reuse_preview = self._preview_env is not None
        if reuse_preview and self._preview_fault != fault.name:
            raise ValueError("Preview and execution must use the same scene condition")
        if reuse_preview and fault.position_jitter:
            raise ValueError("Interactive preview does not support experimental scene perturbations")
        env = self._preview_env if reuse_preview else UR5GraspEnv(headless=self.headless, model_editor=fault.model_editor)
        renderer = None
        report, evaluation, visual, success = None, {}, None, False
        monitor = None
        original_step = None
        stage = "planning"
        try:
            if reuse_preview:
                env.reset_state()
            else:
                env.reset()
            for _ in range(500):
                env.step()
            initial_quat = env.mj_data.body(source).xquat.copy()
            observation = env.render()
            color = cv2.cvtColor(observation["img"], cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(before), color)
            renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
            root_map = renderer.root_map(env.mj_data)
            try:
                plan = self._plan(env, before, instruction, source, destination, params, history)
            except (ValueError, RuntimeError) as exc:
                raise TaskAbort(ErrorReport(ErrorType.PLAN_PARSE_ERROR, str(exc),
                    {"service_error": isinstance(exc, LLMServiceError)}, detector="planner")) from exc
            plan = fault.corrupt_plan(plan, attempt)
            (directory / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2))
            actions = validate_plan(plan, source, destination, lambda n: self._resolve(env, n))
            stage = "perception"
            pixel = actions[0].get("args", {}).get("pixel")
            if fault.name == "grounding" and attempt == 1:
                pixel = project_to_pixel(env, env.mj_data.body("RedBin").xpos)
            pixel = validate_grounding(pixel, observation["depth"], root_map, env.mj_model.body(source).id)
            destination_pixel = actions[2].get("args", {}).get("pixel")
            validate_grounding(destination_pixel, observation["depth"], root_map, env.mj_model.body(destination).id)
            if self.segmentation == "simulation":
                mask = (root_map == env.mj_model.body(source).id).astype(np.uint8) * 255
                # Segmentation/depth rasterization differs at silhouette boundaries across GL drivers.
                mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
                cv2.imwrite(str(directory / "mask.png"), mask)
            else:
                from vlm_process import segment_and_crop_mask
                try:
                    mask = segment_and_crop_mask(image_bgr=color, point_xy=pixel, depth=observation["depth"],
                                                 save_path=str(directory / "mask.png"))
                except (ValueError, RuntimeError) as exc:
                    raise TaskAbort(ErrorReport(ErrorType.MASK_INVALID, str(exc), detector="sam")) from exc
            validate_mask(mask, root_map, env.mj_model.body(source).id)
            try:
                candidates = run_grasp_inference(color, observation["depth"], mask, fovy=env.fovy,
                                                backend=self.grasp_backend, visualize=False)
            except (ValueError, RuntimeError) as exc:
                raise TaskAbort(ErrorReport(ErrorType.NO_GRASP_CANDIDATE, str(exc), detector="grasp_backend")) from exc
            index = min(params.candidate_index, len(candidates) - 1)
            flow = GraspFlow(env, candidates[index:index+1])
            nominal = flow.T_wo.t.copy()
            flow.T_wo = sm.SE3.Trans(*(np.array(fault.grasp_bias()) + params.grasp_offset)) * flow.T_wo
            residual = flow.T_wo.t[:2] - env.mj_data.body(source).xpos[:2]
            stage = "execution"
            monitor = ExecutionMonitor(env, source, destination)
            original_step = env.step
            carry_steps = 0

            def monitored_step(action=None):
                nonlocal carry_steps
                if monitor.phase == "carry":
                    carry_steps += 1
                    if fault.name == "slip" and attempt == 1 and carry_steps >= 350 and action is not None:
                        action[-1] = 0
                original_step(action)
                if carry_steps % 10 == 0:
                    monitor.tick()

            env.step = monitored_step
            try:
                flow.move_to_grasp_pose(time1=params.time_scale, time2=params.time_scale, time3=params.time_scale)
                flow.close_gripper()
                monitor.check_grasp(residual)
                monitor.phase = "carry"
                if self.perception == "simulation":
                    target = env.mj_data.body(destination).xpos.copy()
                else:
                    from grasp_process import camera_calibration_from_env, robust_depth_at_pixel, _pixel2base_xyz
                    transform, intrinsics = camera_calibration_from_env(env)
                    u, v = destination_pixel
                    depth = robust_depth_at_pixel(observation["depth"], u, v)
                    target = np.array(_pixel2base_xyz(u, v, depth, intrinsics, transform))
                target += np.array(fault.place_bias()) + params.place_offset
                flow.move_to_point(tuple(target), z_offset=0.12, lift_height=params.lift_height,
                                   time4=params.time_scale, time5=params.time_scale, time6=params.time_scale)
                monitor.phase = "release"
                flow.open_gripper()
                for _ in range(250):
                    env.step(flow.action)
                flow.back_to_zero()
            except AssertionError as exc:
                raise TaskAbort(ErrorReport(ErrorType.IK_FAILURE, "Inverse kinematics failed", {
                    "grasp_residual_xy": residual.tolist(), "nominal_grasp_xyz": nominal.tolist(),
                    "commanded_grasp_xyz": flow.T_wo.t.tolist()}, detector="ik_solver")) from exc
            stage = "placement"
            success, evaluation, report = evaluate_placement(env, source, destination, initial_quat)
        except TaskAbort as exc:
            report = exc.report
            if stage == "execution":
                report.evidence.setdefault("grasp_residual_xy", residual.tolist())
                report.evidence.setdefault("residual_source", "simulation_ground_truth")
            if env.mj_data is not None:
                _, evaluation, _ = evaluate_placement(env, source, destination, initial_quat)
        finally:
            if original_step is not None:
                env.step = original_step
            if env.mj_renderer is not None:
                cv2.imwrite(str(after), cv2.cvtColor(env.render()["img"], cv2.COLOR_RGB2BGR))
            if renderer is not None:
                renderer.close()
            if not reuse_preview:
                env.close()
        if report is not None:
            report.image_paths = [str(p) for p in (before, after) if p.exists()]
        if self.visual_verify and self.client is not None and after.exists():
            try:
                visual = verify_visual(self.client, str(before), str(after), instruction)
                if success and visual["success"] is False:
                    report = ErrorReport(ErrorType.VISUAL_VERIFICATION_FAILED, visual["reason"],
                                         {"physical_success": True}, image_paths=[str(before), str(after)], detector="vlm")
            except (ValueError, RuntimeError) as exc:
                visual = {"success": None, "reason": str(exc),
                          "status": "api_error" if isinstance(exc, LLMServiceError) else "invalid_response"}
        return {"attempt": attempt, "physical_success": bool(success),
                "accepted": bool(success and report is None), "evaluation": evaluation,
                "visual": visual, "error": report.to_dict() if report else None,
                "parameters": params.to_dict(), "last_stage": stage}, report

    def run(self, *, source=None, destination=None, method="reflection_memory",
            fault="collision", output="logs/reflection/demo", instruction=None, context="default", seed=0):
        if method not in METHODS:
            raise ValueError(f"Unknown method: {method}")
        if method.startswith("reflection") and self.reflector is None:
            raise ValueError("Reflection method requires a reflector")
        fault = Fault(fault)
        started = time.monotonic()
        initial_stats = dict(self.client.stats) if self.client is not None else {}
        task = resolve_task(instruction, source=source, destination=destination,
                            parser=self.task_parser, client=self.client)
        source, destination, instruction = task.source, task.destination, task.instruction
        fault = Fault(fault.name, source, seed, self.scene_jitter)
        print(f"[task] {LABELS[source]} -> {LABELS[destination]} parser={task.parser}", flush=True)
        output = Path(output).resolve()
        output.mkdir(parents=True, exist_ok=True)
        # Context is externally supplied, observable setup identity, never a hidden fault label.
        memory_context = {"setup": context, "source": source, "destination": destination,
                                 "perception": self.perception, "segmentation": self.segmentation,
                                 "backend": self.grasp_backend}
        if self.scene_jitter:
            memory_context["scene_jitter"] = self.scene_jitter
        memory_key = json.dumps(memory_context, sort_keys=True)
        params, history, errors, reflections = Parameters(), [], [], []
        recalled = self.memory.recall(memory_key) if method == "reflection_memory" and self.memory else None
        if recalled:
            params = params.updated(recalled["parameters"])
        records, success = [], False
        attempts = 1 if method == "baseline" else self.max_attempts
        for attempt in range(1, attempts + 1):
            np.random.seed(seed)
            record, report = self._attempt(source, destination, instruction, fault, attempt, params,
                                           output / f"attempt_{attempt}", history)
            records.append(record)
            print(f"[{method}] attempt={attempt} accepted={record['accepted']} "
                  f"error={report.error_type.value if report else 'none'}", flush=True)
            if recalled and attempt == 1:
                self.memory.feedback(memory_key, recalled["signature"], record["accepted"])
            if record["accepted"]:
                success = True
                if method == "reflection_memory" and self.memory:
                    self.memory.remember(memory_key, errors, params, reflections)
                break
            if report and report.evidence.get("service_error"):
                break
            if report:
                errors.append(report)
            if method.startswith("reflection") and attempt < attempts and report:
                try:
                    reflected = self.reflector.reflect(report, params, history)
                    params = params.updated(reflected.changes)
                    reflections.append(reflected)
                    record["reflection"] = reflected.to_dict()
                    history.append({"error": report.to_dict(), "reflection": reflected.to_dict()})
                except (ValueError, RuntimeError) as exc:
                    record["reflection_error"] = str(exc)
                    record["reflection_status"] = "api_error" if isinstance(exc, LLMServiceError) else "invalid_response"
                    break
        result = {"source": source, "destination": destination, "instruction": instruction,
                  "task_resolution": task.to_dict(),
                  "method": method, "fault": fault.name, "persistent_fault": fault.persistent,
                  "context": context, "seed": seed, "success": success, "attempts": len(records),
                  "scene_jitter_m": self.scene_jitter,
                  "elapsed_s": time.monotonic()-started, "memory_hit": recalled is not None,
                  "perception": self.perception, "segmentation": self.segmentation,
                  "reflector": type(self.reflector).__name__ if method.startswith("reflection") else None,
                  "llm_stats": {k: v-initial_stats[k] for k, v in self.client.stats.items()} if self.client else {},
                  "retry_protocol": "restore_same_initial_scene_each_attempt", "records": records}
        temporary = output / "result.json.tmp"
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        temporary.replace(output / "result.json")
        return result

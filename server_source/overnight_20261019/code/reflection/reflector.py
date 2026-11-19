"""Constrained corrections; model failure is never silently labelled as LLM reflection."""
from dataclasses import asdict, dataclass, replace
import json
import math

from .errors import ErrorType


@dataclass(frozen=True)
class Parameters:
    replan: bool = False
    reground: bool = False
    lift_height: float = 0.35
    time_scale: float = 1.0
    grasp_offset: tuple = (0.0, 0.0, 0.0)
    place_offset: tuple = (0.0, 0.0, 0.0)
    candidate_index: int = 0

    def to_dict(self):
        return asdict(self)

    def updated(self, changes):
        if not isinstance(changes, dict):
            raise ValueError("Correction must be an object")
        unknown = set(changes) - set(self.to_dict())
        if unknown:
            raise ValueError(f"Unsupported correction fields: {sorted(unknown)}")
        values = self.to_dict()
        values.update(changes)
        for key in ("replan", "reground"):
            if type(values[key]) is not bool:
                raise ValueError(f"{key} must be boolean")
        for key, lo, hi in (("lift_height", 0.10, 0.48), ("time_scale", 0.5, 3.0)):
            v = values[key]
            if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not lo <= v <= hi:
                raise ValueError(f"{key} must be finite in [{lo}, {hi}]")
        for key in ("grasp_offset", "place_offset"):
            vector = values[key]
            if not isinstance(vector, (list, tuple)) or len(vector) != 3:
                raise ValueError(f"{key} must have three components")
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 0.25 for v in vector):
                raise ValueError(f"{key} components must be finite within 0.25 m")
            values[key] = tuple(float(v) for v in vector)
        if type(values["candidate_index"]) is not int or not 0 <= values["candidate_index"] <= 4:
            raise ValueError("candidate_index must be an integer in [0, 4]")
        return replace(self, **values)


@dataclass
class Reflection:
    cause: str
    changes: dict
    source: str

    def to_dict(self):
        return asdict(self)


class RuleReflector:
    def reflect(self, report, parameters, history=()):
        kind, ev = report.error_type, report.evidence
        changes = {}
        if report.stage.value == "planning":
            changes["replan"] = True
        elif kind in {ErrorType.GROUNDING_OFF_TARGET, ErrorType.GROUNDING_OUT_OF_IMAGE,
                      ErrorType.DEPTH_INVALID, ErrorType.MASK_INVALID}:
            changes["reground"] = True
        elif kind in {ErrorType.EMPTY_GRASP, ErrorType.IK_FAILURE}:
            residual = ev.get("grasp_residual_xy", [0, 0])
            if max(abs(v) for v in residual) > 0.015:
                changes["grasp_offset"] = [parameters.grasp_offset[i] - residual[i] for i in range(2)] + [0.0]
            else:
                changes["candidate_index"] = min(parameters.candidate_index + 1, 4)
        elif kind == ErrorType.COLLISION:
            changes["lift_height"] = min(0.48, max(0.45, parameters.lift_height + 0.10))
        elif kind == ErrorType.OBJECT_DROPPED:
            residual = ev.get("grasp_residual_xy", [0, 0])
            if max(abs(v) for v in residual) > 0.015:
                changes["grasp_offset"] = [parameters.grasp_offset[i] - residual[i] for i in range(2)] + [0.0]
            else:
                changes["time_scale"] = min(3.0, parameters.time_scale * 1.5)
        elif kind == ErrorType.WRONG_OBJECT_GRASPED:
            changes["reground"] = True
        elif kind in {ErrorType.PLACEMENT_OFFSET, ErrorType.OBJECT_OUTSIDE_CONTAINER}:
            residual = ev.get("placement_residual_xy", [0, 0])
            changes["place_offset"] = [parameters.place_offset[i] - residual[i] for i in range(2)] + [0.0]
        elif kind == ErrorType.OBJECT_TOPPLED:
            changes["time_scale"] = min(3.0, parameters.time_scale * 1.5)
        elif kind in {ErrorType.NO_GRASP_CANDIDATE, ErrorType.VISUAL_VERIFICATION_FAILED}:
            changes["reground"] = True
        parameters.updated(changes)
        return Reflection(report.message, changes, "rule")


class LLMReflector:
    def __init__(self, client):
        self.client = client

    def reflect(self, report, parameters, history=()):
        prompt = (
            # 只说明参数含义与取值范围，不给出"某类错误 → 某个修正"的对应关系，
            # 修正方案必须由模型根据证据、图像和历史自行推理。
            "You diagnose a UR5e pick-and-place failure from the error report, the before/after "
            "camera images and the history of earlier attempts in this task. "
            "Return JSON {\"cause\":str,\"changes\":{...}}. Changes are absolute parameter values, "
            "not increments; omit fields you do not want to change.\n"
            "Parameter meanings:\n"
            "- replan (boolean): ask the planner for a new action plan.\n"
            "- reground (boolean): ask the perception module to localize the objects again.\n"
            "- lift_height (0.10..0.48 m): vertical lift after grasping, before moving horizontally.\n"
            "- time_scale (0.5..3): duration multiplier of each motion segment; larger is slower.\n"
            "- grasp_offset / place_offset (3-vector in metres, each component -0.25..0.25): "
            "added to the perceived world position of the grasp / release point.\n"
            "- candidate_index (integer 0..4): which ranked grasp candidate to use.\n"
            "Evidence fields: grasp_residual_xy = commanded grasp xy - object xy; "
            "placement_residual_xy = final object xy - container centre xy; "
            "contacts lists (robot or held body, touched body) pairs.\n"
            "Do not invent coordinates, execute code, or change the task.\n"
            + json.dumps({"error": stable_error(report.to_dict()), "parameters": parameters.to_dict(),
                          "history": [{**item, "error": stable_error(item["error"])} for item in history]}, ensure_ascii=False)
        )
        result = self.client.ask_json(prompt, images=report.image_paths, max_tokens=1000, cache_tag="reflect-v2")
        if not isinstance(result.get("cause"), str) or not result["cause"].strip():
            raise ValueError("Reflection has no cause")
        changes = result.get("changes")
        parameters.updated(changes)
        return Reflection(result["cause"], changes, "llm")


def stable_error(report):
    return {k: v for k, v in report.items() if k not in {"timestamp", "image_paths"}}

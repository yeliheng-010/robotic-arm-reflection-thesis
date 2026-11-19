"""Faults change planner inputs or physical commands, never evaluator results."""
from dataclasses import dataclass
import math

import numpy as np


FAULTS = ("none", "planning", "grounding", "calibration", "collision", "slip", "placement", "unreachable")


@dataclass(frozen=True)
class Fault:
    name: str = "none"
    source: str = "RedBlock"
    scene_seed: int = 0
    position_jitter: float = 0.0

    def __post_init__(self):
        if self.name not in FAULTS:
            raise ValueError(f"Unknown fault: {self.name}")
        if not math.isfinite(self.position_jitter) or not 0 <= self.position_jitter <= 0.015:
            raise ValueError("position_jitter must be within 0..0.015 metres")

    @property
    def persistent(self):
        return self.name in {"calibration", "collision", "placement", "unreachable"}

    def model_editor(self, spec):
        if self.position_jitter:
            body = spec.body(self.source)
            position = np.asarray(body.pos).copy()
            position[:2] += np.random.default_rng(self.scene_seed).uniform(
                -self.position_jitter, self.position_jitter, 2)
            body.pos = position.tolist()
        if self.name == "collision":
            divider = spec.geom("safety_divider")
            divider.size = [divider.size[0], divider.size[1], 0.19]
            divider.pos = [divider.pos[0], divider.pos[1], 0.19]

    def grasp_bias(self):
        return {"calibration": (0, -0.045, 0), "unreachable": (0.15, 0, 0)}.get(self.name, (0, 0, 0))

    def place_bias(self):
        return (-0.17, 0, 0) if self.name == "placement" else (0, 0, 0)

    def corrupt_plan(self, plan, attempt):
        if self.name == "planning" and attempt == 1:
            return {"action_components": [{"action": "open_gripper", "component": ["RedBlock", "center"]}]}
        return plan

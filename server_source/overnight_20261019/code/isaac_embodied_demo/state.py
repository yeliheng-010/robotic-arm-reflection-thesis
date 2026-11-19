"""UI-facing state that stays independent from Isaac Sim imports."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from time import strftime
from typing import Deque, List, Optional


class DemoPhase(str, Enum):
    IDLE = "idle"
    OBSERVE = "observe"
    PLAN = "plan"
    NAVIGATE = "navigate"
    DOCK = "dock"
    APPROACH = "approach"
    DESCEND = "descend"
    ALIGN = "align"
    GRASP = "grasp"
    LIFT = "lift"
    TRANSFER = "transfer"
    PLACE = "place"
    RELEASE = "release"
    RETREAT = "retreat"
    VERIFY = "verify"
    RECOVER = "recover"
    COMPLETED = "completed"
    FAILED = "failed"


PHASE_LABELS = {
    DemoPhase.IDLE: "Waiting for task",
    DemoPhase.OBSERVE: "Reading USD / PhysX world state",
    DemoPhase.PLAN: "Building a skill plan with verification gates",
    DemoPhase.NAVIGATE: "Navigating through the collision-checked home map",
    DemoPhase.DOCK: "Docking the mobile manipulator at a work zone",
    DemoPhase.APPROACH: "Moving above the current object",
    DemoPhase.DESCEND: "Descending slowly to the grasp pose",
    DemoPhase.ALIGN: "Checking end-effector alignment",
    DemoPhase.GRASP: "Closing the parallel gripper",
    DemoPhase.LIFT: "Lifting and validating the grasp",
    DemoPhase.TRANSFER: "Transferring the held object",
    DemoPhase.PLACE: "Descending to the target support",
    DemoPhase.RELEASE: "Releasing the held object",
    DemoPhase.RETREAT: "Retreating to a safe pose",
    DemoPhase.VERIFY: "Checking pose and contact stability",
    DemoPhase.RECOVER: "Recovering and replanning",
    DemoPhase.COMPLETED: "Task completed",
    DemoPhase.FAILED: "Task failed",
}


@dataclass
class DemoState:
    status: str = "idle"
    phase: DemoPhase = DemoPhase.IDLE
    revision: int = 0
    progress: float = 0.0
    active_target: str = "care station"
    current_object: str = "cup"
    robot_zone: str = "living table"
    active_route: str = "stationary"
    completed_objects: List[str] = field(default_factory=list)
    holding: bool = False
    left_finger_contact: bool = False
    right_finger_contact: bool = False
    support_contact: str = "none"
    attachment_mode: str = "none"
    contact_impulse: float = 0.0
    physics_verified: bool = False
    showcase_mode: bool = False
    showcase_event: str = "not armed"
    memory_episodes: int = 0
    last_error: Optional[str] = None
    logs: Deque[str] = field(default_factory=lambda: deque(maxlen=16))

    @property
    def phase_label(self) -> str:
        return PHASE_LABELS[self.phase]

    def log(self, message: str) -> None:
        self.logs.append(f"[{strftime('%H:%M:%S')}] {message}")

    def log_lines(self) -> List[str]:
        return list(self.logs)

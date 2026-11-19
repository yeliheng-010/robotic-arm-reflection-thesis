from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any, Dict, List, Optional, Tuple


Vector3 = Tuple[float, float, float]


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    provider: str
    description: str
    required_inputs: Tuple[str, ...] = ()
    preconditions: Tuple[str, ...] = ()
    safety_rules: Tuple[str, ...] = ()


@dataclass
class WorldEntity:
    entity_id: str
    kind: str
    position: Vector3
    zone: Optional[str] = None
    movable: bool = True
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RobotState:
    x: float
    y: float
    yaw: float = 0.0
    arm_parked: bool = True
    holding: Optional[str] = None
    docked_zone: Optional[str] = None


@dataclass
class WorldSnapshot:
    version: int
    entities: Dict[str, WorldEntity]
    robot: RobotState
    blocked_corridors: Tuple[str, ...] = ()
    occupied_targets: Tuple[str, ...] = ()
    timestamp: float = field(default_factory=time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "entities": {key: value.to_dict() for key, value in self.entities.items()},
            "robot": asdict(self.robot),
            "blocked_corridors": list(self.blocked_corridors),
            "occupied_targets": list(self.occupied_targets),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class GoalItem:
    object_id: str
    target_zone: str
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalSpec:
    instruction: str
    items: List[GoalItem]
    goal_id: str
    constraints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanStep:
    step_id: str
    skill: str
    target: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    expected_world_version: int = 0
    status: str = "pending"
    explanation: str = ""

    def to_request(self) -> "SkillRequest":
        return SkillRequest(
            skill=self.skill,
            target=self.target,
            params=dict(self.params),
            expected_world_version=self.expected_world_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillRequest:
    skill: str
    target: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    expected_world_version: int = 0


@dataclass
class SkillResult:
    skill: str
    success: bool
    message: str
    failure_code: Optional[str] = None
    observed_effects: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryEpisode:
    signature: str
    context: Dict[str, Any]
    repair: Dict[str, Any]
    outcome: str
    task_id: Optional[str] = None
    created_at: float = field(default_factory=time)
    episode_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

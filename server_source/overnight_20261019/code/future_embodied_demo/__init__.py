"""Offline future embodied-intelligence demonstration.

The package intentionally separates the cognitive backend from the simulated
body.  ``FutureAIEmulator`` is deterministic and local; it can later be
replaced by a cloud model without changing the skill or simulator contracts.
"""

from .models import (
    CapabilitySpec,
    GoalItem,
    GoalSpec,
    MemoryEpisode,
    PlanStep,
    SkillRequest,
    SkillResult,
    WorldEntity,
    WorldSnapshot,
)

__all__ = [
    "CapabilitySpec",
    "GoalItem",
    "GoalSpec",
    "MemoryEpisode",
    "PlanStep",
    "SkillRequest",
    "SkillResult",
    "WorldEntity",
    "WorldSnapshot",
]

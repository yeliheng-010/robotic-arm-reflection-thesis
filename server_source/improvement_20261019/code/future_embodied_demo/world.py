from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

from .models import WorldEntity, WorldSnapshot


@dataclass(frozen=True)
class WorldChange:
    kind: str
    entity_id: Optional[str]
    before: object
    after: object


class WorldModel:
    """Thread-safe latest world state plus semantic change detection."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshot: Optional[WorldSnapshot] = None
        self._changes: List[WorldChange] = []

    def update(self, snapshot: WorldSnapshot) -> List[WorldChange]:
        with self._lock:
            changes = self._diff(self._snapshot, snapshot)
            self._snapshot = snapshot
            self._changes = changes
            return list(changes)

    def snapshot(self) -> Optional[WorldSnapshot]:
        with self._lock:
            return self._snapshot

    def changes(self) -> List[WorldChange]:
        with self._lock:
            return list(self._changes)

    @staticmethod
    def _diff(
        previous: Optional[WorldSnapshot], current: WorldSnapshot
    ) -> List[WorldChange]:
        if previous is None:
            return [WorldChange("initial_observation", None, None, current.version)]

        changes: List[WorldChange] = []
        all_ids = set(previous.entities) | set(current.entities)
        for entity_id in sorted(all_ids):
            old = previous.entities.get(entity_id)
            new = current.entities.get(entity_id)
            if old is None or new is None:
                changes.append(WorldChange("entity_set_changed", entity_id, old, new))
                continue
            if old.zone != new.zone:
                changes.append(WorldChange("entity_zone_changed", entity_id, old.zone, new.zone))
            distance_sq = sum((a - b) ** 2 for a, b in zip(old.position, new.position))
            if distance_sq > 0.0025:
                changes.append(
                    WorldChange("entity_moved", entity_id, old.position, new.position)
                )

        if previous.blocked_corridors != current.blocked_corridors:
            changes.append(
                WorldChange(
                    "path_availability_changed",
                    None,
                    previous.blocked_corridors,
                    current.blocked_corridors,
                )
            )
        if previous.occupied_targets != current.occupied_targets:
            changes.append(
                WorldChange(
                    "target_availability_changed",
                    None,
                    previous.occupied_targets,
                    current.occupied_targets,
                )
            )
        if previous.robot.holding != current.robot.holding:
            changes.append(
                WorldChange(
                    "gripper_state_changed",
                    current.robot.holding or previous.robot.holding,
                    previous.robot.holding,
                    current.robot.holding,
                )
            )
        return changes


def entities_by_zone(snapshot: WorldSnapshot) -> Dict[str, List[WorldEntity]]:
    result: Dict[str, List[WorldEntity]] = {}
    for entity in snapshot.entities.values():
        if entity.zone:
            result.setdefault(entity.zone, []).append(entity)
    return result

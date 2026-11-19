"""Simulator-independent task and navigation contract for the Isaac demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


Vector3 = Tuple[float, float, float]
Rectangle = Tuple[float, float, float, float]

TABLE_TOP_Z = 0.768
MOBILE_BASE_Z = 0.39


@dataclass(frozen=True)
class ObjectTask:
    object_id: str
    display_name: str
    source_position: Vector3
    target_zone: str
    target_position: Vector3
    half_height: float
    keep_upright: bool = False


# This is the same goal used by the MuJoCo demonstration: two care items go
# to the care station and the toy goes to the storage bin.
OBJECT_TASKS = (
    ObjectTask(
        "cup",
        "water cup",
        (-2.72, -0.03, TABLE_TOP_Z + 0.0465 + 0.006),
        "care_station",
        (2.48, 1.62, TABLE_TOP_Z + 0.024 + 0.0465 + 0.002),
        0.0465,
        True,
    ),
    ObjectTask(
        "medicine_box",
        "medicine box",
        (-2.98, -0.03, TABLE_TOP_Z + 0.045 + 0.006),
        "care_station",
        (2.83, 1.62, TABLE_TOP_Z + 0.024 + 0.045 + 0.002),
        0.045,
    ),
    ObjectTask(
        "toy",
        "toy block",
        (-2.46, -0.03, TABLE_TOP_Z + 0.045 + 0.006),
        "storage_bin",
        (2.65, -2.25, 0.667),
        0.045,
    ),
)

TASK_BY_ID: Dict[str, ObjectTask] = {task.object_id: task for task in OBJECT_TASKS}

# Dock poses are (x, y, yaw radians).  The Franka's local +X direction faces
# each work surface, so the same downward manipulation policy works at every
# station after the mobile base arrives.
DOCKING_POSES: Dict[str, Vector3] = {
    "living_table": (-2.72, -0.68, 1.57079632679),
    # Match the proven source-table stand-off.  The old 0.96 m pose left the
    # wrist at the edge of Franka's workspace; link 5 then contacted the table
    # before the held object could converge to its release pose.
    "care_station": (2.66, 1.12, 1.57079632679),
    # Keep a common world-facing arm frame throughout transport.  The storage
    # dock therefore sits south of the bin so its target is in Franka's +X
    # work direction, just like both tables and the buffer stand.
    "storage_bin": (2.65, -2.94, 1.57079632679),
    "buffer_tray": (0.90, 2.15, 1.57079632679),
}

# Global planning ends at these collision-free pre-dock poses.  The short
# final approach to the exact dock is executed as a separate straight segment,
# which lets furniture stay correctly inflated in the A* map.
NAVIGATION_POSES: Dict[str, Vector3] = {
    "living_table": (-2.72, -0.92, 1.57079632679),
    "care_station": (2.66, 0.90, 1.57079632679),
    "storage_bin": (1.92, -2.94, 1.57079632679),
    "buffer_tray": (0.90, 2.08, 1.57079632679),
}

# Collision-aware navigation uses the same two-route topology as the MuJoCo
# scene.  Furniture and three divider segments leave a lower and upper gap.
STATIC_NAV_OBSTACLES: Tuple[Rectangle, ...] = (
    (-3.92, -0.43, -1.55, 0.43),  # living table
    (1.50, 1.37, 3.90, 2.23),  # care station
    (2.16, -2.62, 3.14, -1.88),  # storage bin
    (0.30, 2.56, 1.50, 3.36),  # buffer stand
    (-0.08, -3.38, 0.08, -2.48),  # divider south
    (-0.08, -0.78, 0.08, 0.78),  # divider middle
    (-0.08, 2.48, 0.08, 3.38),  # divider north
)

DYNAMIC_CORRIDOR_OBSTACLES: Dict[str, Rectangle] = {
    "corridor_low": (-0.48, -1.95, 0.48, -1.03),
    "corridor_high": (-0.48, 1.03, 0.48, 1.95),
}

DEFAULT_INSTRUCTION = (
    "Move the water cup and medicine box from the living table to the care "
    "station, put the toy in the storage bin, and keep the cup upright."
)

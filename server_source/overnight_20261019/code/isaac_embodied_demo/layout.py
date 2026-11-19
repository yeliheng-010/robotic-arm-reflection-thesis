"""Measured, collision-audited layout for the native Isaac Sim home scene.

This module deliberately has no Isaac Sim imports.  The scene builder consumes
the placements below, while ordinary unit tests can verify that furniture
footprints do not overlap before the expensive simulator is started.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import fmod
from typing import Iterable, Tuple


Vector3 = Tuple[float, float, float]

ROOM_SIZE: Vector3 = (9.0, 7.0, 2.9)
ROOM_INNER_X = (-4.40, 4.40)
ROOM_INNER_Y = (-3.40, 3.40)


@dataclass(frozen=True)
class FurniturePlacement:
    """A visual asset pose plus its measured world-space dimensions."""

    name: str
    asset: str
    position: Vector3
    rotation: Vector3 = (0.0, 0.0, 0.0)
    # Dimensions after the scale declared in assets.py.  Values were measured
    # from the official Isaac 5.1 USD files with tools/inspect_isaac_assets.py.
    size: Vector3 = (0.0, 0.0, 0.0)

    def footprint(self) -> Tuple[float, float, float, float]:
        """Return an axis-aligned (xmin, xmax, ymin, ymax) footprint."""

        yaw = abs(fmod(self.rotation[2], 180.0))
        width, depth = self.size[:2]
        if 45.0 < yaw < 135.0:
            width, depth = depth, width
        x, y = self.position[:2]
        return (x - width / 2.0, x + width / 2.0, y - depth / 2.0, y + depth / 2.0)


# The two task tables use the same measured NVIDIA ArchViz asset.  Local task
# furniture is included in the footprint audit so the navigation map and the
# rendered scene cannot silently diverge.
FURNITURE_LAYOUT = (
    FurniturePlacement("LivingTable", "dining_table", (-2.74, 0.0, 0.0), size=(2.3368, 0.8192, 0.7684)),
    FurniturePlacement("CareTable", "dining_table", (2.70, 1.80, 0.0), size=(2.3368, 0.8192, 0.7684)),
    FurniturePlacement("StorageBin", "local_storage", (2.65, -2.25, 0.0), size=(0.98, 0.74, 0.72)),
    FurniturePlacement("BufferStand", "local_buffer", (0.90, 2.96, 0.0), size=(1.20, 0.80, 0.768)),
    FurniturePlacement("Sofa", "sofa", (-2.70, 2.65, 0.001), size=(2.5935, 0.9909, 0.9663)),
    FurniturePlacement("Fridge", "fridge", (3.38, -0.35, -0.005), size=(1.8655, 0.7006, 1.8359)),
    FurniturePlacement("Plant1", "plant", (-4.00, 1.40, 0.031), size=(0.4463, 0.4148, 0.5067)),
    FurniturePlacement("Plant2", "plant", (4.00, 2.90, 0.031), size=(0.4463, 0.4148, 0.5067)),
)


def unexpected_overlaps(
    placements: Iterable[FurniturePlacement] = FURNITURE_LAYOUT,
    *,
    tolerance: float = 0.002,
) -> list[tuple[str, str]]:
    """Return furniture pairs whose measured floor footprints interpenetrate."""

    items = tuple(placements)
    overlaps: list[tuple[str, str]] = []
    for index, first in enumerate(items):
        ax0, ax1, ay0, ay1 = first.footprint()
        for second in items[index + 1 :]:
            bx0, bx1, by0, by1 = second.footprint()
            overlap_x = min(ax1, bx1) - max(ax0, bx0)
            overlap_y = min(ay1, by1) - max(ay0, by0)
            if overlap_x > tolerance and overlap_y > tolerance:
                overlaps.append((first.name, second.name))
    return overlaps


def outside_room(
    placements: Iterable[FurniturePlacement] = FURNITURE_LAYOUT,
) -> list[str]:
    """Return assets extending through the interior faces of the room walls."""

    outside: list[str] = []
    for placement in placements:
        x0, x1, y0, y1 = placement.footprint()
        if x0 < ROOM_INNER_X[0] or x1 > ROOM_INNER_X[1] or y0 < ROOM_INNER_Y[0] or y1 > ROOM_INNER_Y[1]:
            outside.append(placement.name)
    return outside


def validate_layout() -> None:
    """Fail fast instead of silently composing a visibly invalid USD stage."""

    overlaps = unexpected_overlaps()
    outside = outside_room()
    if overlaps or outside:
        raise ValueError(f"Invalid furniture layout: overlaps={overlaps}, outside={outside}")

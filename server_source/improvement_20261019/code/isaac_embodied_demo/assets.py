"""Asset manifest and measured scene dimensions for the Isaac Sim demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


Vector3 = Tuple[float, float, float]

ASSET_ROOT_DEFAULT = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1"
)


@dataclass(frozen=True)
class AssetSpec:
    relative_path: str
    scale: Vector3 = (1.0, 1.0, 1.0)
    description: str = ""


RESIDENTIAL_ASSETS: Dict[str, AssetSpec] = {
    "cabinet": AssetSpec(
        "/Isaac/Props/Sektion_Cabinet/sektion_cabinet_visuals.usd",
        description="SimReady Sektion kitchen cabinet",
    ),
    "dining_table": AssetSpec(
        "/NVIDIA/Assets/ArchVis/Residential/Furniture/DiningSets/"
        "DesPeres/DesPeres_Table.usd",
        (0.01, 0.01, 0.01),
        "ArchViz dining table",
    ),
    "dining_chair": AssetSpec(
        "/NVIDIA/Assets/ArchVis/Residential/Furniture/DiningSets/"
        "DesPeres/DesPeres_Chair.usd",
        (0.01, 0.01, 0.01),
        "ArchViz dining chair",
    ),
    "sofa": AssetSpec(
        "/NVIDIA/Assets/ArchVis/Residential/Furniture/Sofas/Moline.usd",
        (0.01, 0.01, 0.01),
        "ArchViz residential sofa",
    ),
    "fridge": AssetSpec(
        "/NVIDIA/Assets/ArchVis/Residential/Appliances/Refrigerators/fridge.usd",
        (0.01, 0.01, 0.01),
        "ArchViz refrigerator",
    ),
    "plant": AssetSpec(
        "/NVIDIA/Assets/ArchVis/Residential/Plants/Plant_02.usd",
        (0.01, 0.01, 0.01),
        "ArchViz indoor plant",
    ),
    "glass": AssetSpec(
        "/NVIDIA/Assets/ArchVis/Residential/Kitchen/Kitchenware/Dinnerware/"
        "P_Glassware_Short.usd",
        (0.01, 0.01, 0.01),
        "ArchViz drinking glass",
    ),
    "plate": AssetSpec(
        "/NVIDIA/Assets/ArchVis/Residential/Kitchen/Kitchenware/Dinnerware/"
        "plate_large.usd",
        (0.01, 0.01, 0.01),
        "ArchViz dinner plate",
    ),
    "mug": AssetSpec(
        "/Isaac/Props/YCB/Axis_Aligned/025_mug.usd",
        description="YCB benchmark mug mesh",
    ),
}


# ``sektion_cabinet_visuals.usd`` intentionally has no defaultPrim: its
# visual-only pieces are authored as several root prims.  Referencing those
# roots explicitly keeps the complete photorealistic cabinet while avoiding
# the articulation/rigid-body metadata in the instanceable task asset.
SEKTION_VISUAL_PRIMS = (
    "/sektion_visuals",
    "/door_left_visuals",
    "/door_left_knob_visuals",
    "/door_right_visuals",
    "/door_right_knob_visuals",
    "/drawer_bottom_visuals",
    "/drawer_handle_bottom_visuals",
    "/drawer_top_visuals",
    "/drawer_handle_top_visuals",
)


# These measurements were read from the official USD assets using
# tools/inspect_isaac_assets.py.  The room itself is now authored locally so a
# complete Simple_Room scene (outdoor backdrop, old table and all) is not
# accidentally nested around this second furniture set.
COUNTER_TOP_Z = 0.83
MUG_HALF_HEIGHT = 0.04654
PLATE_TOP_Z = COUNTER_TOP_Z + 0.02857
ROBOT_BASE_POSITION: Vector3 = (-0.45, 0.0, COUNTER_TOP_Z)
INITIAL_MUG_POSITION: Vector3 = (0.20, 0.0, COUNTER_TOP_Z + MUG_HALF_HEIGHT + 0.006)
# Keep both targets inside Franka's reliable near-table workspace.  The old
# x=0.20/y=+-0.29 layout required a near-limit 0.71 m horizontal reach while
# maintaining a downward tool orientation, causing RMPflow to retract.
PRIMARY_PLACE_POSITION: Vector3 = (0.00, -0.27, PLATE_TOP_Z + MUG_HALF_HEIGHT + 0.002)
BUFFER_PLACE_POSITION: Vector3 = (0.00, 0.27, PLATE_TOP_Z + MUG_HALF_HEIGHT + 0.002)


def asset_url(asset_root: str, name: str) -> str:
    return asset_root.rstrip("/") + RESIDENTIAL_ASSETS[name].relative_path

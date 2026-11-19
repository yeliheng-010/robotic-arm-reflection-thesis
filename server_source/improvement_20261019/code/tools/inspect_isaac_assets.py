"""Print authored bounds and physics metadata for the Isaac demo assets.

Run this with the Isaac Sim Python environment, not the project's Python 3.10
environment.  It is intentionally headless and does not modify the assets.
"""

from __future__ import annotations

from isaacsim import SimulationApp


APP = SimulationApp(
    {
        "headless": True,
        "enable_crashreporter": False,
        "limit_cpu_threads": 16,
        "extra_args": ["--/telemetry/enableAnonymousData=false"],
    }
)

import omni.usd
from isaacsim.storage.native import get_assets_root_path
from pxr import PhysxSchema, Usd, UsdGeom, UsdPhysics


RELATIVE_ASSETS = {
    "cabinet": "/Isaac/Props/Sektion_Cabinet/sektion_cabinet_instanceable.usd",
    "dining_table": (
        "/NVIDIA/Assets/ArchVis/Residential/Furniture/DiningSets/"
        "DesPeres/DesPeres_Table.usd"
    ),
    "dining_chair": (
        "/NVIDIA/Assets/ArchVis/Residential/Furniture/DiningSets/"
        "DesPeres/DesPeres_Chair.usd"
    ),
    "sofa": "/NVIDIA/Assets/ArchVis/Residential/Furniture/Sofas/Moline.usd",
    "fridge": (
        "/NVIDIA/Assets/ArchVis/Residential/Appliances/Refrigerators/fridge.usd"
    ),
    "plant": "/NVIDIA/Assets/ArchVis/Residential/Plants/Plant_02.usd",
    "glass": (
        "/NVIDIA/Assets/ArchVis/Residential/Kitchen/Kitchenware/Dinnerware/"
        "P_Glassware_Short.usd"
    ),
    "plate": (
        "/NVIDIA/Assets/ArchVis/Residential/Kitchen/Kitchenware/Dinnerware/"
        "plate_large.usd"
    ),
    "mug": "/Isaac/Props/YCB/Axis_Aligned/025_mug.usd",
    "franka": "/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd",
}


def _physics_counts(root: Usd.Prim) -> dict[str, int]:
    counts = {"rigid": 0, "collision": 0, "ccd": 0, "articulation": 0}
    for prim in Usd.PrimRange(root):
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            counts["rigid"] += 1
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            counts["collision"] += 1
        if prim.HasAPI(PhysxSchema.PhysxRigidBodyAPI):
            counts["ccd"] += 1
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            counts["articulation"] += 1
    return counts


def main() -> None:
    context = omni.usd.get_context()
    context.new_stage()
    APP.update()
    stage = context.get_stage()
    root = get_assets_root_path()

    for name, relative_path in RELATIVE_ASSETS.items():
        prim = stage.DefinePrim(f"/World/{name}", "Xform")
        prim.GetReferences().AddReference(root + relative_path)

    while context.get_stage_loading_status()[2] > 0:
        APP.update()

    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
        useExtentsHint=True,
    )
    print("STAGE", "meters_per_unit", UsdGeom.GetStageMetersPerUnit(stage))
    for name, relative_path in RELATIVE_ASSETS.items():
        prim = stage.GetPrimAtPath(f"/World/{name}")
        bounds = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        minimum = tuple(round(float(value), 5) for value in bounds.GetMin())
        maximum = tuple(round(float(value), 5) for value in bounds.GetMax())
        size = tuple(round(maximum[i] - minimum[i], 5) for i in range(3))
        print(
            "ASSET",
            name,
            "path",
            relative_path,
            "min",
            minimum,
            "max",
            maximum,
            "size",
            size,
            "physics",
            _physics_counts(prim),
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        APP.close()

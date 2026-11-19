"""Build the native Isaac Sim residential scene and its physical objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import omni.kit.app
import omni.usd
from isaacsim.core.api import World
from isaacsim.core.prims import SingleRigidPrim, SingleXFormPrim
from isaacsim.core.utils.rotations import euler_angles_to_quat
from isaacsim.core.utils.viewports import set_camera_view
from isaacsim.robot.manipulators.examples.franka import Franka
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

from .assets import (
    RESIDENTIAL_ASSETS,
    asset_url,
)
from .layout import FURNITURE_LAYOUT, ROOM_SIZE, FurniturePlacement, validate_layout
from .task_config import (
    DOCKING_POSES,
    DYNAMIC_CORRIDOR_OBSTACLES,
    MOBILE_BASE_Z,
    NAVIGATION_POSES,
    OBJECT_TASKS,
    TABLE_TOP_Z,
    TASK_BY_ID,
)


MUG_PATH = "/World/Home/Task/Mug"
MEDICINE_PATH = "/World/Home/Task/MedicineBox"
TOY_PATH = "/World/Home/Task/Toy"
OBJECT_PATHS = {
    "cup": MUG_PATH,
    "medicine_box": MEDICINE_PATH,
    "toy": TOY_PATH,
}
LEFT_FINGER_PATH = "/World/Home/Robot/panda_leftfinger"
RIGHT_FINGER_PATH = "/World/Home/Robot/panda_rightfinger"
LIVING_TABLE_COLLIDER_PATH = "/World/Home/Colliders/LivingTableTop"
CARE_CUP_COLLIDER_PATH = "/World/Home/Task/CareCupPlateCollider"
CARE_MEDICINE_COLLIDER_PATH = "/World/Home/Task/CareMedicinePlateCollider"
STORAGE_COLLIDER_PATH = "/World/Home/Task/StorageBinFloor"
BUFFER_PLATE_COLLIDER_PATH = "/World/Home/Task/BufferPlateCollider"
PRIMARY_PLATE_COLLIDER_PATH = CARE_CUP_COLLIDER_PATH
MOBILE_BASE_PATH = "/World/Home/MobileBase"
DYNAMIC_OBSTACLE_PATH = "/World/Home/Navigation/DynamicObstacle"


@dataclass
class HomeScene:
    world: World
    robot: Franka
    mug: SingleRigidPrim
    objects: dict[str, SingleRigidPrim]
    mobile_base: SingleXFormPrim
    stage: Usd.Stage
    initial_object_positions: dict[str, np.ndarray]
    initial_object_orientations: dict[str, np.ndarray]
    primary_place_position: np.ndarray
    buffer_place_position: np.ndarray
    base_pose: np.ndarray
    navigation_curve: UsdGeom.BasisCurves

    def reset_physical_state(self) -> None:
        """Reset is the only normal path that explicitly restores a mug pose."""

        for object_id, rigid in self.objects.items():
            rigid.set_default_state(
                position=self.initial_object_positions[object_id],
                orientation=self.initial_object_orientations[object_id],
                linear_velocity=np.zeros(3),
                angular_velocity=np.zeros(3),
            )
        self.world.reset()
        for object_id, rigid in self.objects.items():
            rigid.set_world_pose(
                position=self.initial_object_positions[object_id],
                orientation=self.initial_object_orientations[object_id],
            )
            rigid.set_linear_velocity(np.zeros(3))
            rigid.set_angular_velocity(np.zeros(3))
        start = DOCKING_POSES["living_table"]
        self.set_mobile_base_pose(start)
        self.robot.set_solver_position_iteration_count(64)
        self.robot.set_solver_velocity_iteration_count(16)

    def set_mobile_base_pose(self, pose: Sequence[float]) -> None:
        """Move the kinematic chassis and robot root by one continuous step."""

        x, y, yaw = map(float, pose)
        orientation = euler_angles_to_quat(np.array([0.0, 0.0, yaw]))
        self.mobile_base.set_world_pose(
            position=np.array([x, y, 0.20]), orientation=orientation
        )
        self.robot.set_world_pose(
            position=np.array([x, y, MOBILE_BASE_Z]), orientation=orientation
        )
        self.base_pose[:] = (x, y, yaw)

    def show_navigation_path(
        self,
        points: Sequence[Sequence[float]],
        *,
        replanned: bool = False,
    ) -> None:
        """Draw the current A* result inside the native 3-D viewport.

        The curve is visual-only USD geometry.  It deliberately has no
        collision API, so making the planner legible cannot change PhysX.
        """

        if not points:
            self.navigation_curve.CreateCurveVertexCountsAttr().Set([])
            self.navigation_curve.CreatePointsAttr().Set([])
            return
        vertices = [
            Gf.Vec3f(float(point[0]), float(point[1]), 0.035)
            for point in points
        ]
        self.navigation_curve.CreateTypeAttr().Set(UsdGeom.Tokens.linear)
        self.navigation_curve.CreateWrapAttr().Set(UsdGeom.Tokens.nonperiodic)
        self.navigation_curve.CreateCurveVertexCountsAttr().Set([len(vertices)])
        self.navigation_curve.CreatePointsAttr().Set(vertices)
        self.navigation_curve.CreateWidthsAttr().Set([0.055] * len(vertices))
        color = Gf.Vec3f(1.0, 0.28, 0.035) if replanned else Gf.Vec3f(0.02, 0.72, 1.0)
        self.navigation_curve.CreateDisplayColorAttr().Set([color])


def _add_reference(
    stage: Usd.Stage,
    path: str,
    usd_path: str,
    *,
    position: Sequence[float] = (0.0, 0.0, 0.0),
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    scale: Sequence[float] = (1.0, 1.0, 1.0),
    prim_paths: Optional[Sequence[str]] = None,
) -> None:
    parent = UsdGeom.Xform.Define(stage, path)
    xformable = UsdGeom.Xformable(parent)
    xformable.AddTranslateOp().Set(Gf.Vec3d(*position))
    xformable.AddRotateXYZOp().Set(Gf.Vec3f(*rotation))
    xformable.AddScaleOp().Set(Gf.Vec3f(*scale))
    if prim_paths:
        for index, prim_path in enumerate(prim_paths):
            asset = stage.DefinePrim(f"{path}/Asset_{index:02d}", "Xform")
            asset.GetReferences().AddReference(
                Sdf.Reference(assetPath=usd_path, primPath=Sdf.Path(prim_path))
            )
    else:
        asset = stage.DefinePrim(path + "/Asset", "Xform")
        asset.GetReferences().AddReference(usd_path)


def _make_preview_material(
    stage: Usd.Stage,
    path: str,
    color: Sequence[float],
    roughness: float,
) -> UsdShade.Material:
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, path + "/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def _make_physics_material(
    stage: Usd.Stage,
    path: str,
    *,
    static_friction: float,
    dynamic_friction: float,
    restitution: float = 0.0,
) -> UsdShade.Material:
    material = UsdShade.Material.Define(stage, path)
    physics = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    physics.CreateStaticFrictionAttr().Set(static_friction)
    physics.CreateDynamicFrictionAttr().Set(dynamic_friction)
    physics.CreateRestitutionAttr().Set(restitution)
    return material


def _bind_physics_material(prim: Usd.Prim, material: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(
        material,
        bindingStrength=UsdShade.Tokens.strongerThanDescendants,
        materialPurpose="physics",
    )


def _make_box(
    stage: Usd.Stage,
    path: str,
    position: Sequence[float],
    size: Sequence[float],
    *,
    collision: bool,
    visible: bool,
    visual_material: Optional[UsdShade.Material] = None,
    physics_material: Optional[UsdShade.Material] = None,
) -> UsdGeom.Cube:
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    xform = UsdGeom.Xformable(cube)
    xform.AddTranslateOp().Set(Gf.Vec3d(*position))
    xform.AddScaleOp().Set(Gf.Vec3f(*size))
    if collision:
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        physx = PhysxSchema.PhysxCollisionAPI.Apply(cube.GetPrim())
        physx.CreateContactOffsetAttr(0.003)
        physx.CreateRestOffsetAttr(0.0)
    if visual_material is not None:
        UsdShade.MaterialBindingAPI.Apply(cube.GetPrim()).Bind(visual_material)
    if physics_material is not None:
        _bind_physics_material(cube.GetPrim(), physics_material)
    if not visible:
        UsdGeom.Imageable(cube).MakeInvisible()
    return cube


def _make_architectural_shell(
    stage: Usd.Stage,
    surface_material: UsdShade.Material,
) -> None:
    """Create one coherent interior without an inherited outdoor backdrop."""

    floor_material = _make_preview_material(
        stage, "/World/Looks/OakFloor", (0.43, 0.25, 0.11), 0.58
    )
    wall_material = _make_preview_material(
        stage, "/World/Looks/SoftWall", (0.78, 0.80, 0.76), 0.82
    )
    width, depth, height = ROOM_SIZE
    _make_box(
        stage,
        "/World/Home/Architecture/Floor",
        (0.0, 0.0, -0.06),
        (width, depth, 0.12),
        collision=True,
        visible=True,
        visual_material=floor_material,
        physics_material=surface_material,
    )
    # The front is intentionally open for the viewport.  These three walls form
    # a single indoor set and expose no inherited road/grass/HDRI environment.
    _make_box(
        stage,
        "/World/Home/Architecture/BackWall",
        (0.0, depth / 2.0 - 0.04, height / 2.0),
        (width, 0.12, height),
        collision=True,
        visible=True,
        visual_material=wall_material,
        physics_material=surface_material,
    )
    for name, x in (("LeftWall", -width / 2.0 + 0.04), ("RightWall", width / 2.0 - 0.04)):
        _make_box(
            stage,
            f"/World/Home/Architecture/{name}",
            (x, 0.0, height / 2.0),
            (0.12, depth, height),
            collision=True,
            visible=True,
            visual_material=wall_material,
            physics_material=surface_material,
        )


def _make_task_furniture(stage: Usd.Stage, surface_material: UsdShade.Material) -> None:
    """Author the storage bin, buffer stand and two-route divider."""

    storage = _make_preview_material(
        stage, "/World/Looks/StorageGreen", (0.08, 0.46, 0.24), 0.42
    )
    # Elevated open bin: the toy is released into a real collision enclosure.
    _make_box(
        stage,
        STORAGE_COLLIDER_PATH,
        (2.65, -2.25, 0.58),
        (0.88, 0.62, 0.08),
        collision=True,
        visible=True,
        visual_material=storage,
        physics_material=surface_material,
    )
    for name, position, size in (
        ("StorageLeft", (2.21, -2.25, 0.76), (0.05, 0.68, 0.36)),
        ("StorageRight", (3.09, -2.25, 0.76), (0.05, 0.68, 0.36)),
        # The mobile manipulator docks south of the bin and reaches toward +Y,
        # so the far wall belongs on the north edge and the approach side must
        # remain physically open.
        ("StorageBack", (2.65, -1.94, 0.76), (0.88, 0.05, 0.36)),
    ):
        _make_box(
            stage,
            f"/World/Home/Task/{name}",
            position,
            size,
            collision=True,
            visible=True,
            visual_material=storage,
            physics_material=surface_material,
        )
    _make_box(
        stage,
        "/World/Home/Task/StoragePedestal",
        (2.65, -2.25, 0.28),
        (0.80, 0.54, 0.56),
        collision=True,
        visible=True,
        visual_material=storage,
        physics_material=surface_material,
    )

    buffer_material = _make_preview_material(
        stage, "/World/Looks/BufferGold", (0.82, 0.50, 0.06), 0.36
    )
    _make_box(
        stage,
        "/World/Home/Task/BufferStand",
        (0.90, 2.96, TABLE_TOP_Z - 0.04),
        (1.14, 0.80, 0.08),
        collision=True,
        visible=True,
        visual_material=buffer_material,
        physics_material=surface_material,
    )
    for index, (dx, dy) in enumerate(
        ((-0.52, -0.35), (-0.52, 0.35), (0.52, -0.35), (0.52, 0.35))
    ):
        _make_box(
            stage,
            f"/World/Home/Task/BufferLeg{index + 1}",
            (0.90 + dx, 2.96 + dy, 0.34),
            (0.07, 0.07, 0.68),
            collision=True,
            visible=True,
            visual_material=buffer_material,
            physics_material=surface_material,
        )

    divider_material = _make_preview_material(
        stage, "/World/Looks/Divider", (0.20, 0.31, 0.40), 0.24
    )
    for name, y, length in (
        ("South", -2.93, 0.90),
        ("Middle", 0.0, 1.56),
        ("North", 2.93, 0.90),
    ):
        _make_box(
            stage,
            f"/World/Home/Navigation/Divider{name}",
            (0.0, y, 0.48),
            (0.16, length, 0.96),
            collision=True,
            visible=True,
            visual_material=divider_material,
            physics_material=surface_material,
        )

    # Thin floor markers make the two alternative routes legible in the
    # native viewport without becoming collision geometry.
    route_material = _make_preview_material(
        stage, "/World/Looks/RouteMarker", (0.03, 0.48, 0.72), 0.55
    )
    for name, y in (("Low", -1.49), ("High", 1.49)):
        _make_box(
            stage,
            f"/World/Home/Navigation/Route{name}",
            (0.0, y, 0.006),
            (1.10, 0.10, 0.012),
            collision=False,
            visible=True,
            visual_material=route_material,
        )

    # Colored, visual-only zone beacons make the multi-room mission readable
    # from the overview camera.  They sit at collision-free approach poses.
    zone_colors = {
        "living_table": (0.05, 0.56, 0.92),
        "care_station": (0.12, 0.78, 0.38),
        "storage_bin": (0.92, 0.42, 0.05),
        "buffer_tray": (0.86, 0.68, 0.04),
    }
    for zone, position in NAVIGATION_POSES.items():
        marker = UsdGeom.Cylinder.Define(
            stage, f"/World/Home/Navigation/Zone_{zone}"
        )
        marker.CreateAxisAttr("Z")
        marker.CreateRadiusAttr(0.22)
        marker.CreateHeightAttr(0.012)
        marker.CreateDisplayColorAttr().Set([Gf.Vec3f(*zone_colors[zone])])
        UsdGeom.Xformable(marker).AddTranslateOp().Set(
            Gf.Vec3d(float(position[0]), float(position[1]), 0.018)
        )


def _make_static_plate_collider(
    stage: Usd.Stage,
    path: str,
    position: Sequence[float],
    surface_material: UsdShade.Material,
    *,
    surface_z: float = TABLE_TOP_Z,
) -> None:
    collider = UsdGeom.Cylinder.Define(stage, path)
    collider.CreateAxisAttr("Z")
    collider.CreateRadiusAttr(0.155)
    collider.CreateHeightAttr(0.024)
    UsdGeom.Xformable(collider).AddTranslateOp().Set(
        Gf.Vec3d(float(position[0]), float(position[1]), surface_z + 0.012)
    )
    UsdPhysics.CollisionAPI.Apply(collider.GetPrim())
    physx = PhysxSchema.PhysxCollisionAPI.Apply(collider.GetPrim())
    physx.CreateContactOffsetAttr(0.002)
    physx.CreateRestOffsetAttr(0.0)
    _bind_physics_material(collider.GetPrim(), surface_material)
    UsdGeom.Imageable(collider).MakeInvisible()


def _make_mug(
    stage: Usd.Stage,
    asset_root: str,
    grip_material: UsdShade.Material,
) -> None:
    root = UsdGeom.Xform.Define(stage, MUG_PATH).GetPrim()
    visual = stage.DefinePrim(MUG_PATH + "/Visual", "Xform")
    visual.GetReferences().AddReference(asset_url(asset_root, "mug"))

    # The YCB mug is 0.117 x 0.081 x 0.093 m and its handle extends along X.
    # A compound convex proxy represents both the cylindrical body and handle.
    # The body is 74 mm wide, leaving a real 3 mm approach margin per Franka
    # finger at its 80 mm maximum opening.
    body_collision = UsdGeom.Cylinder.Define(stage, MUG_PATH + "/CollisionBody")
    body_collision.CreateAxisAttr("Z")
    body_collision.CreateRadiusAttr(0.037)
    body_collision.CreateHeightAttr(0.090)
    UsdGeom.Xformable(body_collision).AddTranslateOp().Set(Gf.Vec3d(-0.012, 0.0, 0.0))
    UsdPhysics.CollisionAPI.Apply(body_collision.GetPrim())
    body_physx = PhysxSchema.PhysxCollisionAPI.Apply(body_collision.GetPrim())
    body_physx.CreateContactOffsetAttr(0.0015)
    body_physx.CreateRestOffsetAttr(0.0)
    _bind_physics_material(body_collision.GetPrim(), grip_material)
    UsdGeom.Imageable(body_collision).MakeInvisible()

    for name, position, size in (
        ("HandleOuter", (0.049, 0.0, 0.0), (0.014, 0.018, 0.055)),
        ("HandleTop", (0.032, 0.0, 0.025), (0.042, 0.018, 0.012)),
        ("HandleBottom", (0.032, 0.0, -0.025), (0.042, 0.018, 0.012)),
    ):
        _make_box(
            stage,
            f"{MUG_PATH}/{name}",
            position,
            size,
            collision=True,
            visible=False,
            physics_material=grip_material,
        )

    UsdPhysics.RigidBodyAPI.Apply(root).CreateKinematicEnabledAttr().Set(False)
    mass = UsdPhysics.MassAPI.Apply(root)
    mass.CreateMassAttr(0.32)
    # A partly filled household cup is bottom-heavy.  Authoring that measured
    # property keeps an incidental palm/handle touch from unrealistically
    # flipping the cup before the fingers close.
    mass.CreateCenterOfMassAttr().Set(Gf.Vec3f(-0.012, 0.0, -0.026))
    body = PhysxSchema.PhysxRigidBodyAPI.Apply(root)
    body.CreateEnableCCDAttr(True)
    body.CreateSolverPositionIterationCountAttr(48)
    body.CreateSolverVelocityIterationCountAttr(12)
    body.CreateMaxDepenetrationVelocityAttr(1.0)
    body.CreateLinearDampingAttr(0.18)
    body.CreateAngularDampingAttr(1.2)
    contact_report = PhysxSchema.PhysxContactReportAPI.Apply(root)
    contact_report.CreateThresholdAttr().Set(0.0)


def _configure_dynamic_object(
    root: Usd.Prim,
    *,
    mass_kg: float,
) -> None:
    UsdPhysics.RigidBodyAPI.Apply(root).CreateKinematicEnabledAttr().Set(False)
    UsdPhysics.MassAPI.Apply(root).CreateMassAttr(mass_kg)
    body = PhysxSchema.PhysxRigidBodyAPI.Apply(root)
    body.CreateEnableCCDAttr(True)
    body.CreateSolverPositionIterationCountAttr(48)
    body.CreateSolverVelocityIterationCountAttr(12)
    body.CreateMaxDepenetrationVelocityAttr(1.0)
    body.CreateLinearDampingAttr(0.18)
    body.CreateAngularDampingAttr(1.2)
    PhysxSchema.PhysxContactReportAPI.Apply(root).CreateThresholdAttr().Set(0.0)


def _make_medicine_box(
    stage: Usd.Stage,
    grip_material: UsdShade.Material,
) -> None:
    root = UsdGeom.Xform.Define(stage, MEDICINE_PATH).GetPrim()
    carton = _make_preview_material(
        stage, "/World/Looks/MedicineCarton", (0.88, 0.91, 0.94), 0.48
    )
    red = _make_preview_material(
        stage, "/World/Looks/MedicineCross", (0.78, 0.025, 0.03), 0.38
    )
    _make_box(
        stage,
        MEDICINE_PATH + "/Body",
        (0.0, 0.0, 0.0),
        (0.068, 0.052, 0.090),
        collision=True,
        visible=True,
        visual_material=carton,
        physics_material=grip_material,
    )
    # A raised red cross gives the carton an unmistakable household identity;
    # it is visual-only and does not distort the grasp collision proxy.
    for name, position, size in (
        ("CrossHorizontal", (0.0, -0.027, 0.0), (0.040, 0.003, 0.012)),
        ("CrossVertical", (0.0, -0.027, 0.0), (0.012, 0.003, 0.052)),
    ):
        _make_box(
            stage,
            MEDICINE_PATH + "/" + name,
            position,
            size,
            collision=False,
            visible=True,
            visual_material=red,
        )
    _configure_dynamic_object(root, mass_kg=0.18)


def _make_toy(
    stage: Usd.Stage,
    grip_material: UsdShade.Material,
) -> None:
    root = UsdGeom.Xform.Define(stage, TOY_PATH).GetPrim()
    orange = _make_preview_material(
        stage, "/World/Looks/ToyOrange", (0.95, 0.36, 0.035), 0.34
    )
    blue = _make_preview_material(
        stage, "/World/Looks/ToyBlue", (0.04, 0.33, 0.78), 0.30
    )
    _make_box(
        stage,
        TOY_PATH + "/Body",
        (0.0, 0.0, 0.0),
        (0.062, 0.056, 0.090),
        collision=True,
        visible=True,
        visual_material=orange,
        physics_material=grip_material,
    )
    # Four studs make this read as a construction toy instead of a placeholder
    # box while the single convex body keeps contact behavior deterministic.
    for index, (x, y) in enumerate(
        ((-0.018, -0.015), (-0.018, 0.015), (0.018, -0.015), (0.018, 0.015))
    ):
        stud = UsdGeom.Cylinder.Define(stage, f"{TOY_PATH}/Stud{index + 1}")
        stud.CreateAxisAttr("Z")
        stud.CreateRadiusAttr(0.009)
        stud.CreateHeightAttr(0.010)
        UsdGeom.Xformable(stud).AddTranslateOp().Set(Gf.Vec3d(x, y, 0.050))
        UsdShade.MaterialBindingAPI.Apply(stud.GetPrim()).Bind(blue)
    _configure_dynamic_object(root, mass_kg=0.16)


def _make_mobile_base(
    stage: Usd.Stage,
    surface_material: UsdShade.Material,
) -> None:
    root = UsdGeom.Xform.Define(stage, MOBILE_BASE_PATH).GetPrim()
    navy = _make_preview_material(
        stage, "/World/Looks/MobileNavy", (0.035, 0.11, 0.22), 0.30
    )
    cyan = _make_preview_material(
        stage, "/World/Looks/MobileStatus", (0.02, 0.72, 0.88), 0.22
    )
    rubber = _make_preview_material(
        stage, "/World/Looks/WheelRubber", (0.018, 0.02, 0.024), 0.74
    )
    _make_box(
        stage,
        MOBILE_BASE_PATH + "/Chassis",
        (0.0, 0.0, 0.0),
        (0.62, 0.52, 0.28),
        collision=True,
        visible=True,
        visual_material=navy,
        physics_material=surface_material,
    )
    _make_box(
        stage,
        MOBILE_BASE_PATH + "/StatusDeck",
        (0.0, 0.0, 0.155),
        (0.46, 0.36, 0.03),
        collision=False,
        visible=True,
        visual_material=cyan,
    )
    for index, (x, y) in enumerate(
        ((0.22, 0.285), (0.22, -0.285), (-0.22, 0.285), (-0.22, -0.285))
    ):
        wheel = UsdGeom.Cylinder.Define(stage, f"{MOBILE_BASE_PATH}/Wheel{index + 1}")
        wheel.CreateAxisAttr("Y")
        wheel.CreateRadiusAttr(0.095)
        wheel.CreateHeightAttr(0.055)
        UsdGeom.Xformable(wheel).AddTranslateOp().Set(Gf.Vec3d(x, y, -0.07))
        UsdShade.MaterialBindingAPI.Apply(wheel.GetPrim()).Bind(rubber)
    UsdPhysics.RigidBodyAPI.Apply(root).CreateKinematicEnabledAttr().Set(True)
    UsdPhysics.MassAPI.Apply(root).CreateMassAttr(38.0)


def _make_dynamic_obstacle(
    stage: Usd.Stage,
    surface_material: UsdShade.Material,
) -> None:
    red = _make_preview_material(
        stage, "/World/Looks/DynamicObstacle", (0.82, 0.035, 0.025), 0.38
    )
    obstacle = _make_box(
        stage,
        DYNAMIC_OBSTACLE_PATH,
        (0.0, 1.49, 0.42),
        (0.82, 0.72, 0.84),
        collision=True,
        visible=True,
        visual_material=red,
        physics_material=surface_material,
    )
    obstacle.GetPrim().SetActive(False)


def _path_for_placement(placement: FurniturePlacement) -> str:
    if placement.name == "LivingTable":
        return "/World/Home/Furniture/Living/SourceTable"
    if placement.name == "CareTable":
        return "/World/Home/Furniture/Care/StationTable"
    if placement.name == "Sofa":
        return "/World/Home/Furniture/Living/Sofa"
    if placement.name == "Fridge":
        return "/World/Home/Furniture/Kitchen/Fridge"
    if placement.name.startswith("Plant"):
        return "/World/Home/Furniture/Decor/" + placement.name
    raise KeyError(placement.name)


def _add_residential_visuals(stage: Usd.Stage, asset_root: str) -> None:
    for placement in FURNITURE_LAYOUT:
        if placement.asset.startswith("local_"):
            continue
        spec = RESIDENTIAL_ASSETS[placement.asset]
        _add_reference(
            stage,
            _path_for_placement(placement),
            asset_url(asset_root, placement.asset),
            position=placement.position,
            rotation=placement.rotation,
            scale=spec.scale,
        )


def _add_furniture_colliders(
    stage: Usd.Stage,
    surface_material: UsdShade.Material,
) -> None:
    placements = {item.name: item for item in FURNITURE_LAYOUT}

    for table_name, collider_name in (
        ("LivingTable", "LivingTable"),
        ("CareTable", "CareTable"),
    ):
        table = placements[table_name]
        tx, ty, _ = table.position
        _make_box(
            stage,
            f"/World/Home/Colliders/{collider_name}Top",
            (tx, ty, 0.728),
            (2.30, 0.79, 0.08),
            collision=True,
            visible=False,
            physics_material=surface_material,
        )
        for index, (dx, dy) in enumerate(
            ((-1.06, -0.33), (-1.06, 0.33), (1.06, -0.33), (1.06, 0.33))
        ):
            _make_box(
                stage,
                f"/World/Home/Colliders/{collider_name}Leg{index + 1}",
                (tx + dx, ty + dy, 0.34),
                (0.09, 0.09, 0.68),
                collision=True,
                visible=False,
                physics_material=surface_material,
            )

    sofa = placements["Sofa"]
    _make_box(
        stage,
        "/World/Home/Colliders/Sofa",
        (sofa.position[0], sofa.position[1], 0.47),
        (2.56, 0.96, 0.94),
        collision=True,
        visible=False,
        physics_material=surface_material,
    )
    fridge = placements["Fridge"]
    _make_box(
        stage,
        "/World/Home/Colliders/Fridge",
        (fridge.position[0], fridge.position[1], 0.91),
        (1.83, 0.67, 1.82),
        collision=True,
        visible=False,
        physics_material=surface_material,
    )
    for name in ("Plant1", "Plant2"):
        placement = placements[name]
        pot = UsdGeom.Cylinder.Define(stage, f"/World/Home/Colliders/{name}Pot")
        pot.CreateAxisAttr("Z")
        pot.CreateRadiusAttr(0.13)
        pot.CreateHeightAttr(0.28)
        UsdGeom.Xformable(pot).AddTranslateOp().Set(
            Gf.Vec3d(placement.position[0], placement.position[1], 0.14)
        )
        UsdPhysics.CollisionAPI.Apply(pot.GetPrim())
        _bind_physics_material(pot.GetPrim(), surface_material)
        UsdGeom.Imageable(pot).MakeInvisible()


def _add_task_plates(
    stage: Usd.Stage,
    asset_root: str,
    surface_material: UsdShade.Material,
) -> None:
    plate = RESIDENTIAL_ASSETS["plate"]
    for name, position, collider_path, surface_z in (
        (
            "CareCupPlate",
            TASK_BY_ID["cup"].target_position,
            CARE_CUP_COLLIDER_PATH,
            TABLE_TOP_Z,
        ),
        (
            "CareMedicinePlate",
            TASK_BY_ID["medicine_box"].target_position,
            CARE_MEDICINE_COLLIDER_PATH,
            TABLE_TOP_Z,
        ),
        (
            "BufferPlate",
            (0.90, 2.85, TABLE_TOP_Z),
            BUFFER_PLATE_COLLIDER_PATH,
            TABLE_TOP_Z,
        ),
    ):
        _add_reference(
            stage,
            "/World/Home/Task/" + name,
            asset_url(asset_root, "plate"),
            position=(position[0], position[1], surface_z),
            scale=plate.scale,
        )
        _make_static_plate_collider(
            stage,
            collider_path,
            position,
            surface_material,
            surface_z=surface_z,
        )


def _add_target_blocker(
    stage: Usd.Stage,
    surface_material: UsdShade.Material,
) -> None:
    """Author an initially inactive object used by the occupied-target demo."""

    blocker_material = _make_preview_material(
        stage, "/World/Looks/TargetBlocker", (0.55, 0.025, 0.02), 0.4
    )
    blocker = UsdGeom.Cylinder.Define(stage, "/World/Home/Task/PrimaryPlateBlocker")
    blocker.CreateAxisAttr("Z")
    blocker.CreateRadiusAttr(0.085)
    blocker.CreateHeightAttr(0.060)
    UsdGeom.Xformable(blocker).AddTranslateOp().Set(
        Gf.Vec3d(
            TASK_BY_ID["cup"].target_position[0],
            TASK_BY_ID["cup"].target_position[1],
            TABLE_TOP_Z + 0.024 + 0.030,
        )
    )
    UsdPhysics.CollisionAPI.Apply(blocker.GetPrim())
    UsdShade.MaterialBindingAPI.Apply(blocker.GetPrim()).Bind(blocker_material)
    _bind_physics_material(blocker.GetPrim(), surface_material)
    blocker.GetPrim().SetActive(False)


def _bind_gripper_material(
    stage: Usd.Stage,
    grip_material: UsdShade.Material,
) -> None:
    for root_path in (LEFT_FINGER_PATH, RIGHT_FINGER_PATH):
        root = stage.GetPrimAtPath(root_path)
        if not root.IsValid():
            raise RuntimeError(f"Missing Franka finger prim: {root_path}")
        # Franka's collision shapes live below referenced instance prims.  They
        # are read-only instance proxies and are intentionally not returned by
        # a normal PrimRange walk.  A strong physics-purpose binding on the
        # finger rigid-body root is inherited by those collision shapes.
        _bind_physics_material(root, grip_material)


def _add_lighting(stage: Usd.Stage) -> None:
    dome = UsdLux.DomeLight.Define(stage, "/World/Home/Lights/NeutralDome")
    dome.CreateIntensityAttr(260.0)
    dome.CreateColorAttr(Gf.Vec3f(0.82, 0.87, 0.95))
    sun = UsdLux.DistantLight.Define(stage, "/World/Home/Lights/Sun")
    sun.CreateIntensityAttr(1350.0)
    sun.CreateAngleAttr(0.75)
    UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-48.0, 18.0, 32.0))
    fill = UsdLux.RectLight.Define(stage, "/World/Home/Lights/KitchenFill")
    fill.CreateIntensityAttr(3600.0)
    fill.CreateColorAttr(Gf.Vec3f(1.0, 0.82, 0.68))
    fill.CreateWidthAttr(2.8)
    fill.CreateHeightAttr(1.6)
    UsdGeom.Xformable(fill).AddTranslateOp().Set(Gf.Vec3d(0.0, -0.2, 3.0))


def build_home_scene(simulation_app, asset_root: str) -> HomeScene:
    validate_layout()
    world = World(
        physics_dt=1.0 / 120.0,
        # Keep native GUI and headless control on the same one-command /
        # one-PhysX-step cadence.  A 60 Hz render clock with 120 Hz physics
        # advances two solver steps per controller update in GUI mode, which
        # can make event transitions occur before the arm has converged.
        rendering_dt=1.0 / 120.0,
        stage_units_in_meters=1.0,
        backend="numpy",
        device="cpu",
    )
    stage = omni.usd.get_context().get_stage()
    for path in (
        "/World/Home",
        "/World/Home/Architecture",
        "/World/Home/Furniture",
        "/World/Home/Navigation",
        "/World/Home/Colliders",
        "/World/Home/Task",
        "/World/Home/Lights",
        "/World/Looks",
        "/World/PhysicsMaterials",
    ):
        stage.DefinePrim(path, "Xform")

    surface_material = _make_physics_material(
        stage,
        "/World/PhysicsMaterials/HouseholdSurface",
        static_friction=0.85,
        dynamic_friction=0.65,
    )
    grip_material = _make_physics_material(
        stage,
        "/World/PhysicsMaterials/GripperRubber",
        static_friction=1.6,
        dynamic_friction=1.35,
    )

    _make_architectural_shell(stage, surface_material)
    _add_residential_visuals(stage, asset_root)
    _make_task_furniture(stage, surface_material)
    _add_furniture_colliders(stage, surface_material)
    _add_task_plates(stage, asset_root, surface_material)
    _add_target_blocker(stage, surface_material)
    _make_mug(stage, asset_root, grip_material)
    _make_medicine_box(stage, grip_material)
    _make_toy(stage, grip_material)
    _make_mobile_base(stage, surface_material)
    _make_dynamic_obstacle(stage, surface_material)
    _add_lighting(stage)
    navigation_curve = UsdGeom.BasisCurves.Define(
        stage, "/World/Home/Navigation/ActiveAStarPath"
    )

    source_dock = DOCKING_POSES["living_table"]
    base_orientation = euler_angles_to_quat(
        np.array([0.0, 0.0, source_dock[2]])
    )
    mobile_base = world.scene.add(
        SingleXFormPrim(
            prim_path=MOBILE_BASE_PATH,
            name="mobile_chassis",
            position=np.array([source_dock[0], source_dock[1], 0.20]),
            orientation=base_orientation,
            reset_xform_properties=True,
        )
    )
    robot = world.scene.add(
        Franka(
            prim_path="/World/Home/Robot",
            name="home_franka",
            position=np.array([source_dock[0], source_dock[1], MOBILE_BASE_Z]),
            orientation=base_orientation,
        )
    )
    initial_positions = {
        task.object_id: np.array(task.source_position, dtype=float)
        for task in OBJECT_TASKS
    }
    initial_orientations = {
        # Point the handle away from the robot's approach corridor.  This is a
        # semantic grasp affordance, not a kinematic shortcut; the mug remains
        # a fully dynamic compound rigid body after reset.
        "cup": euler_angles_to_quat(np.array([0.0, 0.0, np.pi])),
        "medicine_box": np.array([1.0, 0.0, 0.0, 0.0]),
        "toy": np.array([1.0, 0.0, 0.0, 0.0]),
    }
    objects: dict[str, SingleRigidPrim] = {}
    for object_id, prim_path, mass in (
        ("cup", MUG_PATH, 0.32),
        ("medicine_box", MEDICINE_PATH, 0.18),
        ("toy", TOY_PATH, 0.16),
    ):
        rigid = world.scene.add(
            SingleRigidPrim(
                prim_path=prim_path,
                name=object_id,
                position=initial_positions[object_id],
                orientation=initial_orientations[object_id],
                mass=mass,
                reset_xform_properties=True,
            )
        )
        rigid.set_default_state(
            position=initial_positions[object_id],
            orientation=initial_orientations[object_id],
            linear_velocity=np.zeros(3),
            angular_velocity=np.zeros(3),
        )
        objects[object_id] = rigid

    while omni.usd.get_context().get_stage_loading_status()[2] > 0:
        simulation_app.update()

    _bind_gripper_material(stage, grip_material)
    physics = world.get_physics_context()
    physics.set_solver_type("TGS")
    physics.enable_ccd(True)
    physics.enable_stablization(True)
    # The referenced Franka asset initializes both finger joints at zero
    # (fully closed).  Pick/place must approach with an actually open gripper;
    # make that the reset state instead of relying on a visual assumption.
    robot.gripper.set_default_state(np.array([0.04, 0.04]))
    world.reset()
    robot.set_solver_position_iteration_count(64)
    robot.set_solver_velocity_iteration_count(16)

    set_camera_view(
        eye=np.array([7.15, -7.10, 5.65]),
        target=np.array([0.0, 0.05, 0.72]),
        camera_prim_path="/OmniverseKit_Persp",
    )
    world.play()

    return HomeScene(
        world=world,
        robot=robot,
        mug=objects["cup"],
        objects=objects,
        mobile_base=mobile_base,
        stage=stage,
        initial_object_positions=initial_positions,
        initial_object_orientations=initial_orientations,
        primary_place_position=np.array(TASK_BY_ID["cup"].target_position),
        buffer_place_position=np.array(
            [0.90, 2.85, TABLE_TOP_Z + 0.024 + 0.0465 + 0.002]
        ),
        base_pose=np.array(source_dock, dtype=float),
        navigation_curve=navigation_curve,
    )

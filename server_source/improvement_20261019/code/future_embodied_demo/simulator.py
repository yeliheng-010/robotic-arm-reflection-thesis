from __future__ import annotations

import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import mujoco
import numpy as np
import spatialmath as sm

from .models import RobotState, SkillRequest, SkillResult, WorldEntity, WorldSnapshot
from .navigation import AStarNavigator, GridSpec, Point2, Rectangle


ROOT = Path(__file__).resolve().parents[1]
MANIPULATOR_ROOT = ROOT / "manipulator_grasp"
if str(MANIPULATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(MANIPULATOR_ROOT))

from arm.robot import UR5e  # noqa: E402
from manipulator_grasp.utils import mj as mj_utils  # noqa: E402


OBJECT_BODIES = {
    "cup": ("Cup", "cup_free"),
    "medicine_box": ("MedicineBox", "medicine_box_free"),
    "toy": ("Toy", "toy_free"),
    "remote": ("Remote", "remote_free"),
    "target_blocker": ("TargetBlocker", "target_blocker_free"),
}

DOCKING_POSES: Dict[str, Tuple[float, float, float]] = {
    "living_table": (1.35, 1.40, 0.0),
    "care_station": (4.75, 2.40, 0.0),
    "storage_bin": (4.55, 1.35, 0.0),
    "buffer_tray": (3.82, 2.88, 0.0),
}

# Collision-free pre-dock points.  ``dock`` performs the final slow approach
# underneath furniture overhangs after navigation has stopped.
NAVIGATION_GOALS: Dict[str, Tuple[float, float, float]] = {
    "living_table": (1.00, 1.72, 0.0),
    "care_station": (4.30, 2.38, 0.0),
    "storage_bin": (4.22, 1.45, 0.0),
    "buffer_tray": (3.82, 2.88, 0.0),
}

STATIC_OBSTACLES: Tuple[Rectangle, ...] = (
    (0.87, 0.37, 2.23, 1.33),  # living table
    (4.47, 2.73, 5.63, 3.57),  # care station
    (4.62, 0.43, 5.48, 1.13),  # storage bin
    (3.53, 3.33, 4.17, 3.77),  # buffer tray
    (3.04, 0.00, 3.16, 0.74),
    (3.04, 1.45, 3.16, 2.55),
    (3.04, 3.26, 3.16, 4.00),
)


class _ViewerAwareRLock:
    """Re-entrant Python lock that also honors MuJoCo viewer ownership.

    MuJoCo's passive viewer requires model/data writes to hold ``viewer.lock``.
    The wrapper acquires that lock only at the outermost nesting level, so
    existing nested simulator helpers remain safe without stalling rendering
    for an entire multi-second skill.
    """

    def __init__(self, owner) -> None:
        self._owner = owner
        self._python_lock = threading.RLock()
        self._local = threading.local()

    def __enter__(self):
        self._python_lock.acquire()
        depth = getattr(self._local, "depth", 0)
        viewer_context = None
        try:
            if depth == 0 and self._owner._viewer_handle is not None:
                viewer_context = self._owner._viewer_handle.lock()
                viewer_context.__enter__()
            self._local.depth = depth + 1
            if depth == 0:
                self._local.viewer_context = viewer_context
            return self
        except Exception:
            self._python_lock.release()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        depth = getattr(self._local, "depth", 1) - 1
        self._local.depth = depth
        try:
            if depth == 0:
                viewer_context = getattr(self._local, "viewer_context", None)
                self._local.viewer_context = None
                if viewer_context is not None:
                    viewer_context.__exit__(exc_type, exc_value, traceback)
        finally:
            self._python_lock.release()


class MobileHomeSimulator:
    """MuJoCo-backed mobile-manipulation skill provider.

    Navigation and holding are kinematically controlled for repeatability, but
    every pose is advanced continuously in MuJoCo and released objects settle
    under physics.  The class exposes typed skills instead of joint commands.
    """

    PARK_Q = np.array([0.0, -1.25, 1.65, -1.95, -1.57, 0.0])

    def __init__(
        self,
        *,
        scene_path: str | Path | None = None,
        realtime: bool = True,
        frame_callback=None,
    ) -> None:
        self.scene_path = Path(scene_path or (
            MANIPULATOR_ROOT / "assets" / "scenes" / "home_mobile_scene.xml"
        ))
        self.realtime = realtime
        self.frame_callback = frame_callback
        self._viewer_handle = None
        self._lock = _ViewerAwareRLock(self)
        self._version = 0
        self._event_revision = 0
        self._base_pose = np.array([0.8, 2.0, 0.0], dtype=float)
        self._holding: Optional[str] = None
        self._arm_parked = True
        self._docked_zone: Optional[str] = None
        self._renderer = None
        self._renderer_model = None
        self._latest_frame: Optional[np.ndarray] = None
        self._last_frame_time = 0.0
        self._navigator = AStarNavigator(
            GridSpec(0.25, 5.75, 0.25, 3.75, 0.10, 0.27)
        )
        self.reset()

    def reset(self) -> WorldSnapshot:
        with self._lock:
            self.mj_model = mujoco.MjModel.from_xml_path(str(self.scene_path))
            self.mj_data = mujoco.MjData(self.mj_model)
            self.camera_name = "cam"
            self.width = 960
            self.height = 640
            self._base_pose[:] = (0.8, 2.0, 0.0)
            self._holding = None
            self._arm_parked = True
            self._docked_zone = None
            self._version += 1
            self._event_revision += 1

            self._base_body_id = self._body_id("ur5e_base")
            self._chassis_mocap_id = self.mj_model.body_mocapid[
                self._body_id("mobile_chassis")
            ]
            self._obstacle_mocap_id = self.mj_model.body_mocapid[
                self._body_id("dynamic_obstacle")
            ]
            self._joint_names = (
                "shoulder_pan_joint",
                "shoulder_lift_joint",
                "elbow_joint",
                "wrist_1_joint",
                "wrist_2_joint",
                "wrist_3_joint",
            )
            self._joint_qpos = np.array(
                [self.mj_model.jnt_qposadr[self._joint_id(name)] for name in self._joint_names]
            )
            self.robot = UR5e()
            self.robot.set_tool(
                sm.SE3.Trans(0.0, 0.0, 0.13)
                * sm.SE3.RPY(-np.pi / 2, -np.pi / 2, 0.0)
            )
            self._set_base_pose(self._base_pose, forward=False)
            self._set_arm_q(self.PARK_Q, forward=False)
            mujoco.mj_forward(self.mj_model, self.mj_data)

            flange = self.mj_data.body("flange")
            flange_pose = sm.SE3.Rt(
                np.asarray(flange.xmat).reshape(3, 3), np.asarray(flange.xpos).copy()
            )
            mj_utils.attach(self.mj_model, self.mj_data, "attach", "2f85", flange_pose)
            mujoco.mj_forward(self.mj_model, self.mj_data)
            for _ in range(120):
                mujoco.mj_step(self.mj_model, self.mj_data)
            self._set_base_pose(self._base_pose)
            self._set_arm_q(self.PARK_Q)
            self._home_state = {
                "qpos": self.mj_data.qpos.copy(),
                "model_body_pos": self.mj_model.body_pos.copy(),
                "model_body_quat": self.mj_model.body_quat.copy(),
                "mocap_pos": self.mj_data.mocap_pos.copy(),
                "mocap_quat": self.mj_data.mocap_quat.copy(),
                "eq_active": self.mj_data.eq_active.copy(),
            }
            self._emit_frame(force=True)
            return self.observe()

    def soft_reset(self) -> WorldSnapshot:
        """Restore the home state without replacing model/data objects.

        This variant keeps a native MuJoCo viewer attached to the same model
        while resetting the physical episode and preserving cloud memory.
        """
        with self._lock:
            home = self._home_state
            self.mj_model.body_pos[:] = home["model_body_pos"]
            self.mj_model.body_quat[:] = home["model_body_quat"]
            self.mj_data.qpos[:] = home["qpos"]
            self.mj_data.qvel[:] = 0.0
            self.mj_data.ctrl[:] = 0.0
            self.mj_data.mocap_pos[:] = home["mocap_pos"]
            self.mj_data.mocap_quat[:] = home["mocap_quat"]
            self.mj_data.eq_active[:] = home["eq_active"]
            self._base_pose[:] = (0.8, 2.0, 0.0)
            self._holding = None
            self._arm_parked = True
            self._docked_zone = None
            self.robot.set_joint(self.PARK_Q)
            self.robot.robot.base = sm.SE3.Trans(0.8, 2.0, 0.43)
            mujoco.mj_forward(self.mj_model, self.mj_data)
            self._version += 1
            self._event_revision += 1
            self._emit_frame(force=True)
            return self.observe()

    def close(self) -> None:
        self.close_renderer()

    def attach_viewer(self, viewer_handle) -> None:
        with self._lock:
            self._viewer_handle = viewer_handle

    def detach_viewer(self) -> None:
        with self._lock:
            self._viewer_handle = None

    def close_renderer(self) -> None:
        with self._lock:
            if self._renderer is not None:
                self._renderer.close()
                self._renderer = None
                self._renderer_model = None

    def observe(self) -> WorldSnapshot:
        with self._lock:
            entities: Dict[str, WorldEntity] = {}
            for entity_id, (body_name, _) in OBJECT_BODIES.items():
                position = tuple(float(v) for v in self.mj_data.body(body_name).xpos)
                zone = self._zone_for(position)
                attributes = {
                    "display_name": {
                        "cup": "水杯",
                        "medicine_box": "药盒",
                        "toy": "玩具",
                        "remote": "遥控器",
                        "target_blocker": "临时障碍物",
                    }[entity_id]
                }
                if entity_id == "cup":
                    quat = np.asarray(self.mj_data.body(body_name).xquat)
                    attributes["upright"] = bool(abs(float(quat[0])) > 0.92)
                if entity_id == "target_blocker" and zone == "care_station":
                    attributes["occupies_target"] = "care_station"
                entities[entity_id] = WorldEntity(
                    entity_id, "household_object", position, zone, True, attributes
                )

            blocked = self._blocked_corridors()
            occupied = tuple(
                sorted(
                    {
                        str(entity.attributes["occupies_target"])
                        for entity in entities.values()
                        if entity.attributes.get("occupies_target")
                    }
                )
            )
            return WorldSnapshot(
                version=self._version,
                entities=entities,
                robot=RobotState(
                    float(self._base_pose[0]),
                    float(self._base_pose[1]),
                    float(self._base_pose[2]),
                    self._arm_parked,
                    self._holding,
                    self._docked_zone,
                ),
                blocked_corridors=blocked,
                occupied_targets=occupied,
            )

    def execute(self, request: SkillRequest) -> SkillResult:
        dispatch = {
            "navigate": self._navigate,
            "dock": self._dock,
            "grasp": self._grasp,
            "place": self._place,
            "recover": self._recover,
            "verify": self._verify,
            "observe": lambda _: SkillResult("observe", True, "世界状态已刷新"),
        }
        handler = dispatch.get(request.skill)
        if handler is None:
            return SkillResult(request.skill, False, "设备未实现该技能", "unsupported_skill")
        try:
            return handler(request)
        except Exception as exc:
            return SkillResult(
                request.skill,
                False,
                f"技能执行异常：{type(exc).__name__}: {exc}",
                "execution_error",
            )

    def inject_event(
        self, event_type: str, *, target: Optional[str] = None
    ) -> Dict[str, object]:
        with self._lock:
            if event_type == "path_blocked":
                corridor = target or "corridor_low"
                position = (3.10, 1.10, 0.35) if corridor != "corridor_high" else (3.10, 2.90, 0.35)
                self.mj_data.mocap_pos[self._obstacle_mocap_id] = position
                message = f"现场加入障碍，阻塞 {corridor}"
            elif event_type == "object_moved":
                object_id = target or "cup"
                if object_id not in OBJECT_BODIES:
                    raise ValueError(f"unknown object: {object_id}")
                if self._holding == object_id:
                    self._holding = None
                body_name, joint_name = OBJECT_BODIES[object_id]
                position = np.asarray(self.mj_data.body(body_name).xpos).copy()
                position[:2] += np.array([0.18, 0.22])
                self._set_free_object_pose(joint_name, position)
                message = f"用户移动了 {object_id}"
            elif event_type == "grasp_lost":
                if self._holding is None:
                    raise RuntimeError("当前没有被夹持物体")
                object_id = self._holding
                _, joint_name = OBJECT_BODIES[object_id]
                position = np.asarray(self.mj_data.site("pinch").xpos).copy()
                # Place the released object just above the floor.  It remains
                # a MuJoCo free body and can be recovered from an ad-hoc dock.
                position[2] = 0.10
                self._holding = None
                self._set_free_object_pose(joint_name, position)
                message = f"{object_id} 从夹爪中脱落"
            elif event_type == "target_occupied":
                target_zone = target or "care_station"
                site = self._target_site(target_zone, "target_blocker")
                self._set_free_object_pose("target_blocker_free", site)
                message = f"{target_zone} 被临时物体占用"
            elif event_type == "clear_obstacle":
                self.mj_data.mocap_pos[self._obstacle_mocap_id] = (-2.0, -2.0, 0.35)
                message = "动态通道障碍已移除"
            else:
                raise ValueError(f"unsupported event type: {event_type}")
            mujoco.mj_forward(self.mj_model, self.mj_data)
            self._version += 1
            self._event_revision += 1
            self._emit_frame(force=True)
            return {
                "event": event_type,
                "target": target,
                "message": message,
                "world_version": self._version,
            }

    def render(self) -> np.ndarray:
        with self._lock:
            if self._renderer is not None and self._renderer_model is not self.mj_model:
                self._renderer.close()
                self._renderer = None
                self._renderer_model = None
            if self._renderer is None:
                self._renderer = mujoco.Renderer(
                    self.mj_model, height=self.height, width=self.width
                )
                self._renderer_model = self.mj_model
            self._renderer.update_scene(self.mj_data, camera=self.camera_name)
            self._latest_frame = self._renderer.render().copy()
            return self._latest_frame.copy()

    def latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    # -- skill implementations -------------------------------------------------

    def _navigate(self, request: SkillRequest) -> SkillResult:
        if not self._arm_parked:
            return SkillResult("navigate", False, "机械臂未收拢，安全层拒绝移动", "unsafe_state")
        target_zone = request.target or ""
        if target_zone not in DOCKING_POSES and not target_zone.startswith("object:"):
            return SkillResult("navigate", False, "未知目标区域", "unknown_zone")
        # Leave a furniture overhang through the same controlled approach used
        # by ``dock`` before asking the global navigator for a route.
        with self._lock:
            previous_dock = self._docked_zone
            undock_start = self._base_pose.copy()
        if previous_dock:
            undock_goal = np.asarray(
                NAVIGATION_GOALS.get(previous_dock, tuple(undock_start)), dtype=float
            )
            for index in range(1, 13):
                alpha = index / 12.0
                with self._lock:
                    self._set_base_pose(undock_start + (undock_goal - undock_start) * alpha)
                    self._emit_frame()
                self._pace(0.012)
            with self._lock:
                self._docked_zone = None
        goal_pose = self._navigation_goal(request)
        goal = goal_pose[:2]
        with self._lock:
            obstacles = self._obstacle_rectangles() + self._remembered_route_obstacles(request)
            path = self._navigator.plan(tuple(self._base_pose[:2]), goal, obstacles)
            planned_event_revision = self._event_revision
        if not path:
            return SkillResult("navigate", False, "没有可用路径", "path_blocked")

        travelled = 0.0
        for start, end in zip(path, path[1:]):
            distance = math.dist(start, end)
            count = max(1, int(math.ceil(distance / 0.035)))
            for index in range(1, count + 1):
                alpha = index / count
                point = (
                    start[0] + (end[0] - start[0]) * alpha,
                    start[1] + (end[1] - start[1]) * alpha,
                )
                with self._lock:
                    if self._event_revision != planned_event_revision:
                        remaining = [tuple(self._base_pose[:2]), point, end, *path[path.index(end) + 1 :]]
                        if not self._navigator.path_is_clear(remaining, self._obstacle_rectangles()):
                            self._version += 1
                            return SkillResult(
                                "navigate",
                                False,
                                "移动过程中检测到新障碍并安全停车",
                                "path_blocked",
                                {"stopped_at": self._base_pose[:2].tolist()},
                                {"travelled_m": travelled},
                            )
                        planned_event_revision = self._event_revision
                    self._set_base_pose((point[0], point[1], 0.0))
                    travelled += distance / count
                    self._emit_frame()
                self._pace(0.012)
        with self._lock:
            self._docked_zone = None
            self._version += 1
        return SkillResult(
            "navigate",
            True,
            f"已到达 {target_zone} 附近",
            observed_effects={"base_pose": self._base_pose.tolist(), "path": path},
            metrics={"travelled_m": travelled, "waypoints": float(len(path))},
        )

    def _dock(self, request: SkillRequest) -> SkillResult:
        target_zone = request.target or ""
        if target_zone not in DOCKING_POSES and not target_zone.startswith("object:"):
            return SkillResult("dock", False, "未知停靠区", "unknown_zone")
        if target_zone.startswith("object:"):
            goal = np.asarray(self._dynamic_object_dock(request), dtype=float)
            pre_dock = goal.copy()
        else:
            goal = np.asarray(DOCKING_POSES[target_zone], dtype=float)
            pre_dock = np.asarray(NAVIGATION_GOALS[target_zone], dtype=float)
        with self._lock:
            distance = float(np.linalg.norm(self._base_pose[:2] - pre_dock[:2]))
            if distance > 0.18:
                return SkillResult("dock", False, "尚未到达可停靠范围", "not_at_zone")
            start = self._base_pose.copy()
        for index in range(1, 13):
            alpha = index / 12.0
            with self._lock:
                self._set_base_pose(start + (goal - start) * alpha)
                self._emit_frame()
            self._pace(0.012)
        with self._lock:
            self._docked_zone = target_zone
            self._version += 1
            self._emit_frame(force=True)
        return SkillResult("dock", True, f"已在 {target_zone} 建立稳定停靠位")

    def _grasp(self, request: SkillRequest) -> SkillResult:
        object_id = request.target or ""
        if object_id not in OBJECT_BODIES:
            return SkillResult("grasp", False, "目标物体不存在", "object_missing")
        with self._lock:
            if self._holding is not None:
                return SkillResult("grasp", False, "夹爪中已有物体", "gripper_occupied")
            object_pos = np.asarray(
                self.mj_data.body(OBJECT_BODIES[object_id][0]).xpos
            ).copy()
            reach = float(np.linalg.norm(object_pos[:2] - self._base_pose[:2]))
            if self._docked_zone is None or reach > 1.10:
                return SkillResult(
                    "grasp", False, "目标已不在当前停靠位的可达范围", "object_moved"
                )
            profile = str(request.params.get("profile", "normal"))
            self._arm_parked = False

        approach = object_pos.copy()
        approach[2] += 0.22
        grasp_point = object_pos.copy()
        grasp_point[2] += 0.10
        q_approach = self._solve_ik(approach)
        q_grasp = self._solve_ik(grasp_point, q0=q_approach)
        if q_approach is None or q_grasp is None:
            with self._lock:
                self._arm_parked = True
            return SkillResult("grasp", False, "目标超出机械臂工作空间", "unreachable")

        self._animate_arm(q_approach, 32)
        self._animate_arm(q_grasp, 24)
        self._animate_gripper(210.0 if profile == "secure" else 175.0)
        with self._lock:
            self._holding = object_id
            self._follow_held_object()
            self._version += 1
            self._emit_frame(force=True)
        self._animate_arm(q_approach, 24)
        self._animate_arm(self.PARK_Q, 32)
        with self._lock:
            self._arm_parked = True
            self._version += 1
        return SkillResult(
            "grasp",
            True,
            f"已使用 {profile} 策略抓取 {object_id}",
            observed_effects={"holding": object_id, "profile": profile},
            metrics={"reach_m": reach},
        )

    def _place(self, request: SkillRequest) -> SkillResult:
        target_zone = request.target or ""
        with self._lock:
            object_id = self._holding
            if object_id is None:
                return SkillResult("place", False, "运输中未检测到夹持物体", "grasp_lost")
            if self._docked_zone != target_zone:
                return SkillResult("place", False, "未在目标区域停靠", "not_docked")
            snapshot = self.observe()
            if target_zone in snapshot.occupied_targets and object_id != "target_blocker":
                return SkillResult("place", False, "目标区域已被占用", "target_occupied")
            target_pos = self._target_site(target_zone, object_id)
            self._arm_parked = False

        approach = target_pos.copy()
        approach[2] += 0.20
        release = target_pos.copy()
        release[2] += 0.10
        q_approach = self._solve_ik(approach)
        q_release = self._solve_ik(release, q0=q_approach)
        if q_approach is None or q_release is None:
            return SkillResult("place", False, "放置点超出机械臂工作空间", "unreachable")
        self._animate_arm(q_approach, 30)
        self._animate_arm(q_release, 22)
        with self._lock:
            _, joint_name = OBJECT_BODIES[object_id]
            final_pos = target_pos.copy()
            self._set_free_object_pose(joint_name, final_pos, upright=True)
            self._holding = None
            self.mj_data.ctrl[-1] = 0.0
        # Clear the released object before advancing physics; otherwise the
        # kinematic demonstration gripper can start the object inside a pad.
        self._animate_arm(q_approach, 20)
        self._animate_arm(self.PARK_Q, 35)
        self._animate_gripper(0.0)
        with self._lock:
            for _ in range(80):
                mujoco.mj_step(self.mj_model, self.mj_data)
            self._version += 1
            self._emit_frame(force=True)
        with self._lock:
            self._arm_parked = True
            self._version += 1
        return SkillResult(
            "place",
            True,
            f"已将 {object_id} 放入 {target_zone}",
            observed_effects={"object_id": object_id, "target_zone": target_zone},
        )

    def _recover(self, request: SkillRequest) -> SkillResult:
        self._animate_arm(self.PARK_Q, 30)
        with self._lock:
            self._arm_parked = True
            self._version += 1
        return SkillResult("recover", True, "机械臂已回到安全收拢姿态")

    def _verify(self, request: SkillRequest) -> SkillResult:
        object_id = request.target or ""
        target_zone = str(request.params.get("target_zone", ""))
        snapshot = self.observe()
        entity = snapshot.entities.get(object_id)
        if entity is None:
            return SkillResult("verify", False, "验证对象不存在", "object_missing")
        if entity.zone != target_zone:
            return SkillResult(
                "verify",
                False,
                f"{object_id} 实际位于 {entity.zone}，预期为 {target_zone}",
                "placement_mismatch",
                {"actual_zone": entity.zone, "target_zone": target_zone},
            )
        constraints = request.params.get("constraints", {}) or {}
        if constraints.get("upright") and not entity.attributes.get("upright"):
            return SkillResult(
                "verify", False, "水杯未保持直立", "orientation_mismatch"
            )
        return SkillResult(
            "verify",
            True,
            f"已验证 {object_id} 位于 {target_zone}",
            observed_effects={"actual_zone": entity.zone},
        )

    # -- model helpers ---------------------------------------------------------

    def _set_base_pose(self, pose: Sequence[float], *, forward: bool = True) -> None:
        x, y, yaw = (float(v) for v in pose)
        self._base_pose[:] = (x, y, yaw)
        self.mj_model.body_pos[self._base_body_id] = (x, y, 0.43)
        quat = np.array([math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0)])
        self.mj_model.body_quat[self._base_body_id] = quat
        self.mj_data.mocap_pos[self._chassis_mocap_id] = (x, y, 0.22)
        self.mj_data.mocap_quat[self._chassis_mocap_id] = quat
        self.robot.robot.base = sm.SE3.Trans(x, y, 0.43) * sm.SE3.Rz(yaw)
        if forward:
            mujoco.mj_forward(self.mj_model, self.mj_data)
            self._sync_gripper_to_flange()
            if self._holding:
                self._follow_held_object()

    def _set_arm_q(self, q: Sequence[float], *, forward: bool = True) -> None:
        values = np.asarray(q, dtype=float)
        self.mj_data.qpos[self._joint_qpos] = values
        self.mj_data.qvel[
            [self.mj_model.jnt_dofadr[self._joint_id(name)] for name in self._joint_names]
        ] = 0.0
        self.robot.set_joint(values)
        if forward:
            mujoco.mj_forward(self.mj_model, self.mj_data)
            self._sync_gripper_to_flange()
            if self._holding:
                self._follow_held_object()

    def _animate_arm(self, target_q: Sequence[float], frames: int) -> None:
        with self._lock:
            start_q = self.mj_data.qpos[self._joint_qpos].copy()
        for index in range(1, frames + 1):
            alpha = 0.5 - 0.5 * math.cos(math.pi * index / frames)
            with self._lock:
                self._set_arm_q(start_q + (np.asarray(target_q) - start_q) * alpha)
                self._emit_frame()
            self._pace(0.012)

    def _animate_gripper(self, target: float) -> None:
        with self._lock:
            start = float(self.mj_data.ctrl[-1])
        for index in range(1, 18):
            value = start + (target - start) * (index / 17.0)
            with self._lock:
                self.mj_data.ctrl[-1] = value
                for _ in range(3):
                    mujoco.mj_step(self.mj_model, self.mj_data)
                if self._holding:
                    self._follow_held_object()
                self._emit_frame()
            self._pace(0.008)

    def _solve_ik(
        self, point: Sequence[float], *, q0: Optional[Sequence[float]] = None
    ) -> Optional[np.ndarray]:
        target = sm.SE3.Trans(*point) * sm.SE3.RPY(-np.pi / 2, -np.pi / 2, 0.0)
        seed = np.asarray(q0 if q0 is not None else self.PARK_Q, dtype=float)
        solution = self.robot.robot.ikine_LM(target, q0=seed, ilimit=80)
        if not solution.success or solution.residual > 1e-3:
            return None
        return np.asarray(solution.q, dtype=float)

    def _follow_held_object(self) -> None:
        if not self._holding:
            return
        _, joint_name = OBJECT_BODIES[self._holding]
        position = np.asarray(self.mj_data.site("pinch").xpos).copy()
        self._set_free_object_pose(joint_name, position, upright=True, forward=False)
        mujoco.mj_forward(self.mj_model, self.mj_data)

    def _sync_gripper_to_flange(self) -> None:
        flange = self.mj_data.body("flange")
        joint_id = self._joint_id("2f85")
        qpos_addr = self.mj_model.jnt_qposadr[joint_id]
        dof_addr = self.mj_model.jnt_dofadr[joint_id]
        self.mj_data.qpos[qpos_addr : qpos_addr + 7] = (
            *np.asarray(flange.xpos),
            *np.asarray(flange.xquat),
        )
        self.mj_data.qvel[dof_addr : dof_addr + 6] = 0.0
        mujoco.mj_forward(self.mj_model, self.mj_data)

    def _set_free_object_pose(
        self,
        joint_name: str,
        position: Sequence[float],
        *,
        upright: bool = True,
        forward: bool = True,
    ) -> None:
        joint_id = self._joint_id(joint_name)
        qpos_addr = self.mj_model.jnt_qposadr[joint_id]
        dof_addr = self.mj_model.jnt_dofadr[joint_id]
        quat = (1.0, 0.0, 0.0, 0.0) if upright else tuple(
            self.mj_data.qpos[qpos_addr + 3 : qpos_addr + 7]
        )
        self.mj_data.qpos[qpos_addr : qpos_addr + 7] = (*position, *quat)
        self.mj_data.qvel[dof_addr : dof_addr + 6] = 0.0
        if forward:
            mujoco.mj_forward(self.mj_model, self.mj_data)

    def _target_site(self, zone: str, object_id: str) -> np.ndarray:
        if zone == "care_station":
            name = "care_cup_slot" if object_id == "cup" else "care_medicine_slot"
        elif zone == "storage_bin":
            name = "storage_bin_site"
        elif zone == "buffer_tray":
            name = "buffer_tray_site"
        elif zone == "living_table":
            name = "living_table_site"
        else:
            raise ValueError(f"unknown target zone: {zone}")
        position = np.asarray(self.mj_data.site(name).xpos).copy()
        if zone == "buffer_tray":
            position[0] += 0.12 if object_id == "target_blocker" else -0.12
        clearance = {
            "cup": 0.050,
            "medicine_box": 0.020,
            "toy": 0.040,
            "remote": 0.020,
            "target_blocker": 0.030,
        }.get(object_id, 0.030)
        position[2] += clearance
        return position

    def _navigation_goal(self, request: SkillRequest) -> Tuple[float, float, float]:
        target = request.target or ""
        if target in NAVIGATION_GOALS:
            return NAVIGATION_GOALS[target]
        return self._dynamic_object_dock(request)

    def _dynamic_object_dock(self, request: SkillRequest) -> Tuple[float, float, float]:
        target = request.target or ""
        object_id = target.split(":", 1)[1] if ":" in target else ""
        if object_id in OBJECT_BODIES:
            position = np.asarray(
                self.mj_data.body(OBJECT_BODIES[object_id][0]).xpos
            ).copy()
        else:
            position = np.asarray(request.params.get("object_position", (0.8, 2.0, 0.0)))
        # Choose one of four approach sides that remains within room bounds.
        candidates = (
            (position[0], position[1] + 0.55, 0.0),
            (position[0], position[1] - 0.55, 0.0),
            (position[0] - 0.55, position[1], 0.0),
            (position[0] + 0.55, position[1], 0.0),
        )
        obstacles = self._obstacle_rectangles()
        for candidate in candidates:
            x, y, _ = candidate
            if not (0.32 <= x <= 5.68 and 0.32 <= y <= 3.68):
                continue
            if all(not (x1 <= x <= x2 and y1 <= y <= y2) for x1, y1, x2, y2 in obstacles):
                return tuple(float(v) for v in candidate)
        return tuple(float(v) for v in candidates[0])

    def _zone_for(self, position: Sequence[float]) -> str:
        x, y, z = position
        if 0.83 <= x <= 2.27 and 0.32 <= y <= 1.38 and z >= 0.60:
            return "living_table"
        if 4.42 <= x <= 5.68 and 2.68 <= y <= 3.62 and z >= 0.55:
            return "care_station"
        if 4.55 <= x <= 5.55 and 0.35 <= y <= 1.20 and z <= 0.65:
            return "storage_bin"
        if 3.45 <= x <= 4.22 and 3.25 <= y <= 3.85 and z >= 0.42:
            return "buffer_tray"
        if self._holding and OBJECT_BODIES[self._holding][0] in (
            "Cup",
            "MedicineBox",
            "Toy",
            "Remote",
            "TargetBlocker",
        ):
            body_name = OBJECT_BODIES[self._holding][0]
            if np.linalg.norm(position[:2] - self.mj_data.body(body_name).xpos[:2]) < 1e-5:
                return "in_gripper"
        return "floor"

    def _obstacle_rectangles(self) -> List[Rectangle]:
        result = list(STATIC_OBSTACLES)
        pos = self.mj_data.mocap_pos[self._obstacle_mocap_id]
        if pos[0] >= 0.0:
            result.append((pos[0] - 0.34, pos[1] - 0.30, pos[0] + 0.34, pos[1] + 0.30))
        return result

    def _blocked_corridors(self) -> Tuple[str, ...]:
        pos = self.mj_data.mocap_pos[self._obstacle_mocap_id]
        blocked = []
        if abs(float(pos[0]) - 3.1) < 0.5:
            if abs(float(pos[1]) - 1.1) < 0.5:
                blocked.append("corridor_low")
            if abs(float(pos[1]) - 2.9) < 0.5:
                blocked.append("corridor_high")
        return tuple(blocked)

    @staticmethod
    def _remembered_route_obstacles(request: SkillRequest) -> List[Rectangle]:
        result: List[Rectangle] = []
        for corridor in request.params.get("avoid_corridors", ()) or ():
            if corridor == "corridor_low":
                result.append((2.76, 0.80, 3.44, 1.40))
            elif corridor == "corridor_high":
                result.append((2.76, 2.60, 3.44, 3.20))
        return result

    def _body_id(self, name: str) -> int:
        result = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, name)
        if result < 0:
            raise KeyError(f"missing MuJoCo body: {name}")
        return result

    def _joint_id(self, name: str) -> int:
        result = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if result < 0:
            raise KeyError(f"missing MuJoCo joint: {name}")
        return result

    def _emit_frame(self, *, force: bool = False) -> None:
        if self.frame_callback is None:
            return
        now = time.monotonic()
        if not force and now - self._last_frame_time < 0.08:
            return
        self._last_frame_time = now
        # Rendering is owned by the dashboard's dedicated render thread.  EGL
        # contexts cannot safely migrate between the engine and HTTP threads.
        self.frame_callback(None)

    def _pace(self, seconds: float) -> None:
        if self.realtime:
            time.sleep(seconds)

"""Closed-loop Franka pick/place orchestration for the native Isaac demo."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
from isaacsim.core.utils.rotations import (
    euler_angles_to_quat,
    quat_to_rot_matrix,
    rot_matrix_to_quat,
)
from isaacsim.core.utils.transformations import pose_from_tf_matrix, tf_matrix_from_pose
from isaacsim.core.utils.xforms import get_world_pose
from isaacsim.robot.manipulators.examples.franka.controllers import PickPlaceController
from isaacsim.sensors.physics import _sensor
from pxr import Gf, Sdf, UsdGeom, UsdPhysics

from future_embodied_demo.memory import MemoryStore
from future_embodied_demo.models import MemoryEpisode
from future_embodied_demo.navigation import AStarNavigator, GridSpec

from .scene import (
    BUFFER_PLATE_COLLIDER_PATH,
    CARE_CUP_COLLIDER_PATH,
    CARE_MEDICINE_COLLIDER_PATH,
    DYNAMIC_OBSTACLE_PATH,
    LEFT_FINGER_PATH,
    LIVING_TABLE_COLLIDER_PATH,
    MUG_PATH,
    OBJECT_PATHS,
    PRIMARY_PLATE_COLLIDER_PATH,
    RIGHT_FINGER_PATH,
    STORAGE_COLLIDER_PATH,
    HomeScene,
)
from .state import DemoPhase, DemoState
from .task_config import (
    DOCKING_POSES,
    DYNAMIC_CORRIDOR_OBSTACLES,
    NAVIGATION_POSES,
    OBJECT_TASKS,
    STATIC_NAV_OBSTACLES,
    TABLE_TOP_Z,
    TASK_BY_ID,
)


EVENT_PHASES: Dict[int, DemoPhase] = {
    0: DemoPhase.APPROACH,
    1: DemoPhase.DESCEND,
    2: DemoPhase.ALIGN,
    3: DemoPhase.GRASP,
    4: DemoPhase.LIFT,
    5: DemoPhase.TRANSFER,
    6: DemoPhase.PLACE,
    7: DemoPhase.RELEASE,
    8: DemoPhase.RETREAT,
    9: DemoPhase.VERIFY,
}

# Small perception-calibrated offsets align the RMPflow control frame with the
# physical center between Franka's asymmetric finger collision meshes.  These
# alter the robot target only; task-object poses remain entirely PhysX-driven.
GRASP_POSITION_OFFSETS = {
    "cup": np.zeros(3),
    "medicine_box": np.array([0.0, 0.006, 0.0]),
    "toy": np.array([0.0, 0.006, 0.0]),
}


class HomeTaskController:
    """Observe-plan-act-verify controller backed by PhysX contacts and joints."""

    JOINT_PATH = "/World/Home/Task/ActiveGraspJoint"
    HAND_PATH = "/World/Home/Robot/panda_hand"
    MAX_CONTACT_WAIT_STEPS = 180
    MAX_RELEASE_WAIT_STEPS = 480

    def __init__(
        self,
        scene: HomeScene,
        state: DemoState,
        memory_path: str | Path,
    ) -> None:
        self.scene = scene
        self.state = state
        self.memory = MemoryStore(memory_path)
        self._contact_interface = _sensor.acquire_contact_sensor_interface()
        self._run_id = 0
        self.controller = self._new_pick_place_controller()
        self._task_index = 0
        self._current_object_id = OBJECT_TASKS[0].object_id
        self._current_object_path = OBJECT_PATHS[self._current_object_id]
        self._current_rigid = self.scene.objects[self._current_object_id]
        self._current_target_zone = OBJECT_TASKS[0].target_zone
        self._target_support_path = CARE_CUP_COLLIDER_PATH
        self._active_place_position = np.array(
            OBJECT_TASKS[0].target_position, dtype=float
        )
        self._arrived_for_current_target = False
        self._retry_count = 0
        self._navigator = AStarNavigator(
            GridSpec(-4.15, 4.15, -3.15, 3.15, 0.10, 0.34)
        )
        self._navigation_path: list[tuple[float, float]] = []
        self._navigation_waypoint = 0
        self._navigation_mode = ""
        self._navigation_destination = ""
        self._navigation_dock_pose: Optional[tuple[float, float, float]] = None
        self._blocked_corridors: set[str] = set()
        self._staging_due_to_occupancy = False
        self._last_event = -1
        self._joint_active = False
        self._joint_age_steps = 0
        self._attachment_relative_transform = np.eye(4)
        self._transport_hand_orientation = euler_angles_to_quat(
            np.array([0.0, np.pi, 0.0])
        )
        self._joint_age_steps = 0
        self._settle_steps = 0
        self._reobserve_wait_steps = 0
        self._reobserve_reason = ""
        self._release_wait_steps = 0
        self._grasp_contact_wait_steps = 0
        self._grasp_hand_offset = np.zeros(3)
        self._last_contact_bodies: set[str] = set()
        self._event_diagnostics: list[dict] = []
        self.state.memory_episodes = self.memory.count()
        self.state.log("Native Isaac Sim demo ready: RTX + PhysX, no browser renderer.")
        self.state.log(
            "Collision-audited multi-zone home loaded; all task objects remain dynamic rigid bodies."
        )

    def _new_pick_place_controller(self) -> PickPlaceController:
        return PickPlaceController(
            name=f"home_pick_place_{self._run_id}",
            gripper=self.scene.robot.gripper,
            robot_articulation=self.scene.robot,
            end_effector_initial_height=1.26,
            # Values advance the controller's normalized event clock, not PhysX
            # seconds.  Contact gates below can hold a phase for extra steps.
            events_dt=[0.006, 0.004, 0.05, 0.04, 0.006, 0.004, 0.003, 0.08, 0.008, 0.05],
        )

    def _select_task(self, index: int) -> None:
        task = OBJECT_TASKS[index]
        self._current_object_id = task.object_id
        self._current_object_path = OBJECT_PATHS[task.object_id]
        self._current_rigid = self.scene.objects[task.object_id]
        self._current_target_zone = task.target_zone
        self._active_place_position = np.array(task.target_position, dtype=float)
        self._target_support_path = {
            "cup": CARE_CUP_COLLIDER_PATH,
            "medicine_box": CARE_MEDICINE_COLLIDER_PATH,
            "toy": STORAGE_COLLIDER_PATH,
        }[task.object_id]
        self._staging_due_to_occupancy = False
        self.state.current_object = task.object_id
        self.state.active_target = task.target_zone

    def _reset_run_fields(self) -> None:
        self._last_event = -1
        self._settle_steps = 0
        self._reobserve_wait_steps = 0
        self._reobserve_reason = ""
        self._release_wait_steps = 0
        self._grasp_contact_wait_steps = 0
        self._grasp_hand_offset = np.zeros(3)
        self._attachment_relative_transform = np.eye(4)
        self._navigation_path = []
        self._navigation_waypoint = 0
        self._navigation_mode = ""
        self._navigation_destination = ""
        self._navigation_dock_pose = None
        self.state.left_finger_contact = False
        self.state.right_finger_contact = False
        self.state.support_contact = "none"
        self.state.attachment_mode = "none"
        self.state.physics_verified = False

    def start(self) -> None:
        if self.state.status == "running":
            self.state.log("The task is already running.")
            return
        self._remove_grasp_joint()
        self._run_id += 1
        self._task_index = 0
        self._select_task(0)
        self.controller = self._new_pick_place_controller()
        self._reset_run_fields()
        self._blocked_corridors.clear()
        self._staging_due_to_occupancy = False
        self._arrived_for_current_target = False
        self._retry_count = 0
        self.state.status = "running"
        self.state.phase = DemoPhase.OBSERVE
        self.state.revision += 1
        self.state.progress = 0.02
        self.state.active_target = self._current_target_zone
        self.state.current_object = self._current_object_id
        self.state.robot_zone = "living table"
        self.state.active_route = "stationary at source"
        self.state.completed_objects.clear()
        self.state.holding = False
        self.state.last_error = None
        self.state.log(
            "Observed three household objects, four work zones, two routes, robot, and live contacts."
        )
        self.state.log(
            f"Persistent memory connected: {self.state.memory_episodes} prior episodes available."
        )
        self.state.phase = DemoPhase.PLAN
        self.state.log(
            "Plan r%d: cup + medicine to care, toy to storage; grasp, navigate, place, verify each."
            % self.state.revision
        )
        self.scene.world.play()

    def reset(self) -> None:
        self._remove_grasp_joint()
        blocker = self.scene.stage.GetPrimAtPath("/World/Home/Task/PrimaryPlateBlocker")
        if blocker.IsValid():
            blocker.SetActive(False)
        self.scene.reset_physical_state()
        self.controller = self._new_pick_place_controller()
        self._task_index = 0
        self._select_task(0)
        self._reset_run_fields()
        self._blocked_corridors.clear()
        self._staging_due_to_occupancy = False
        self._arrived_for_current_target = False
        self._retry_count = 0
        self.state.status = "idle"
        self.state.phase = DemoPhase.IDLE
        self.state.progress = 0.0
        self.state.active_target = self._current_target_zone
        self.state.current_object = self._current_object_id
        self.state.robot_zone = "living table"
        self.state.active_route = "stationary at source"
        self.state.completed_objects.clear()
        self.state.holding = False
        self.state.last_error = None
        self.state.showcase_mode = False
        self.state.showcase_event = "not armed"
        self.scene.show_navigation_path([])
        self.state.log("Scene reset in place; SQLite long-term memory was retained.")
        self.scene.world.play()

    def update(self) -> None:
        self._refresh_contact_state()
        if self._reobserve_wait_steps > 0:
            self._reobserve_wait_steps -= 1
            if self._reobserve_wait_steps == 0:
                self._restart_from_observation(self._reobserve_reason)
            return
        if self.state.status != "running":
            return

        if self._joint_active:
            self._joint_age_steps += 1
            # Let a newly authored joint enter the PhysX solver before testing
            # its pose residual.  This is still a measured continuity gate; it
            # only avoids treating the solver's first few frames as a break.
            continuity_tolerance = 0.10 if self._navigation_mode else 0.025
            if self._joint_age_steps > 12 and not self._attachment_is_continuous(
                tolerance=continuity_tolerance
            ):
                self._handle_lost_attachment("the physical grasp constraint separated")
                return

        if self._navigation_mode:
            self._update_navigation()
            return

        if self.controller.is_done():
            if self._settle_steps == 0:
                self._settle_steps = 120
                self.state.phase = DemoPhase.VERIFY
                self.state.log("Motion complete; waiting for dynamic contact and velocity to settle.")
            else:
                self._settle_steps -= 1
                if self._settle_steps == 0:
                    self._verify_result()
            return

        event = self.controller.get_current_event()
        if event != self._last_event:
            self._last_event = event
            phase = EVENT_PHASES.get(event, DemoPhase.VERIFY)
            self.state.phase = phase
            item_base = self._task_index / len(OBJECT_TASKS)
            item_progress = min(0.94, 0.05 + event * 0.095)
            self.state.progress = item_base + item_progress / len(OBJECT_TASKS)
            self.state.log(self.state.phase_label)
            mug_position, mug_orientation = self._current_rigid.get_world_pose()
            _, hand_orientation = get_world_pose(self.HAND_PATH)
            self._event_diagnostics.append(
                {
                    "revision": self.state.revision,
                    "object": self._current_object_id,
                    "event": event,
                    "mug": np.round(mug_position, 4).tolist(),
                    "mug_q": np.round(mug_orientation, 4).tolist(),
                    "control": np.round(
                        self._get_controlled_frame_position(), 4
                    ).tolist(),
                    "hand_q": np.round(hand_orientation, 4).tolist(),
                    "target_hand_q": np.round(
                        self._transport_hand_orientation, 4
                    ).tolist(),
                    "finger_q": np.round(
                        self.scene.robot.gripper.get_joint_positions(), 4
                    ).tolist(),
                    "contacts": sorted(self._last_contact_bodies),
                }
            )

        if event == 5 and self._joint_active and not self._arrived_for_current_target:
            self._begin_navigation(self._current_target_zone, mode="to_target")
            return

        if event == 4 and not self._joint_active:
            grasp_result = self._try_create_physical_grasp()
            if grasp_result is None:
                self.scene.robot.apply_action(self.scene.robot.gripper.forward(action="close"))
                return
            if not grasp_result:
                self._fail_and_recover(
                    self.state.last_error or "Dual-finger PhysX contact was not established"
                )
                return

        if event == 7 and self._joint_active:
            mug_position, _ = self._current_rigid.get_world_pose()
            place_error = float(
                np.linalg.norm(np.asarray(mug_position) - self._active_place_position)
            )
            linear_speed = float(np.linalg.norm(self._current_rigid.get_linear_velocity()))
            if place_error > 0.045 or linear_speed > 0.08:
                if self._release_wait_steps >= self.MAX_RELEASE_WAIT_STEPS:
                    self.state.status = "failed"
                    self.state.phase = DemoPhase.FAILED
                    self.state.last_error = (
                        f"Release gate timed out: error {place_error:.3f} m, "
                        f"speed {linear_speed:.3f} m/s; retaining the physical grasp"
                    )
                    self.state.log(self.state.last_error)
                    return
                if self._release_wait_steps == 0:
                    self.state.phase = DemoPhase.PLACE
                    self.state.log(
                        "Release gate: holding the joint until pose and velocity are safe."
                    )
                self._release_wait_steps += 1
                hold_action = self.controller._cspace_controller.forward(
                    target_end_effector_position=(
                        self._active_place_position + self._grasp_hand_offset
                    ),
                    target_end_effector_orientation=euler_angles_to_quat(
                        np.array([0.0, np.pi, 0.0])
                    ) if not self._joint_active else self._transport_hand_orientation,
                )
                self.scene.robot.apply_action(hold_action)
                return
            self.state.log(
                f"Release gate passed: error {place_error:.3f} m, speed {linear_speed:.3f} m/s."
            )
            self._remove_grasp_joint()
            self.state.holding = False

        mug_position, _ = self._current_rigid.get_world_pose()
        action = self.controller.forward(
            picking_position=(
                np.asarray(mug_position, dtype=float)
                + GRASP_POSITION_OFFSETS[self._current_object_id]
            ),
            placing_position=self._active_place_position + self._grasp_hand_offset,
            current_joint_positions=self.scene.robot.get_joint_positions(),
            end_effector_offset=np.zeros(3),
            end_effector_orientation=(
                self._transport_hand_orientation if self._joint_active else None
            ),
        )
        self.scene.robot.apply_action(action)

    def _navigation_obstacles(self) -> list[tuple[float, float, float, float]]:
        obstacles = list(STATIC_NAV_OBSTACLES)
        obstacles.extend(
            DYNAMIC_CORRIDOR_OBSTACLES[name]
            for name in sorted(self._blocked_corridors)
        )
        return obstacles

    def _begin_navigation(self, destination: str, *, mode: str) -> None:
        dock = self._resolve_dock_pose(destination, mode)
        start = tuple(float(v) for v in self.scene.base_pose[:2])
        if float(np.linalg.norm(np.asarray(start) - np.asarray(dock[:2]))) <= 0.05:
            self._navigation_mode = mode
            self._navigation_destination = destination
            self._navigation_dock_pose = dock
            self._finish_navigation()
            return
        start_zone = next(
            (
                zone
                for zone, pose in DOCKING_POSES.items()
                if float(np.linalg.norm(np.asarray(start) - np.asarray(pose[:2])))
                <= 0.08
            ),
            None,
        )
        # A carried object determines a task-specific lateral dock, so the
        # chassis may not be close to the nominal station pose after release.
        # The semantic zone still tells us which collision-free pre-dock point
        # to retreat through before invoking A*.
        semantic_zone = self.state.robot_zone.replace(" ", "_")
        if start_zone is None and semantic_zone in NAVIGATION_POSES:
            start_zone = semantic_zone
        plan_start = NAVIGATION_POSES[start_zone][:2] if start_zone else start
        plan_goal = NAVIGATION_POSES[destination][:2]
        global_path = self._navigator.plan(
            plan_start, plan_goal, self._navigation_obstacles()
        )
        if not global_path:
            self.state.status = "failed"
            self.state.phase = DemoPhase.FAILED
            self.state.last_error = f"No collision-free route to {destination}"
            self.state.log(self.state.last_error)
            return
        path: list[tuple[float, float]] = [start]
        if float(np.linalg.norm(np.asarray(start) - np.asarray(plan_start))) > 0.01:
            path.append(tuple(plan_start))
        path.extend(global_path[1:])
        if float(np.linalg.norm(np.asarray(path[-1]) - np.asarray(dock[:2]))) > 0.01:
            path.append(tuple(dock[:2]))
        self._navigation_path = path
        self._navigation_waypoint = 1
        self._navigation_mode = mode
        self._navigation_destination = destination
        self._navigation_dock_pose = dock
        crossing = min(path, key=lambda point: abs(point[0]))
        route = "upper corridor" if crossing[1] >= 0.0 else "lower corridor"
        self.state.phase = DemoPhase.NAVIGATE
        self.state.robot_zone = "en route"
        self.state.active_route = route
        self.state.active_target = destination
        self.scene.show_navigation_path(
            path,
            replanned=bool(self._blocked_corridors),
        )
        carrying = self._current_object_id if self._joint_active else "nothing"
        self.state.log(
            f"A* route: {route}, {len(path)} waypoints; carrying {carrying} to {destination}."
        )

    def _resolve_dock_pose(
        self, destination: str, mode: str
    ) -> tuple[float, float, float]:
        """Choose a dock that aligns the carried object before arm descent.

        Translating a holonomic base is both safer and more capable than asking
        Franka to sweep a grasped object laterally at table height.  While the
        FixedJoint is active, preserve the measured object/base offset and
        solve the chassis pose that puts the object directly above its target.
        No object pose is authored here; PhysX carries it with the robot.
        """

        default = DOCKING_POSES[destination]
        if mode == "to_source":
            object_position, _ = self._current_rigid.get_world_pose()
            # Reproduce the centered, 0.65 m stand-off used by the successful
            # cup grasp for every source object.  Lateral chassis alignment is
            # safer than making the arm reach diagonally across neighbouring
            # objects on the same table.
            return (
                float(object_position[0]),
                float(object_position[1] - 0.65),
                float(default[2]),
            )
        if mode != "to_target" or not self._joint_active:
            return default
        object_position, _ = self._current_rigid.get_world_pose()
        carried_offset = np.asarray(object_position[:2]) - self.scene.base_pose[:2]
        dock_xy = self._active_place_position[:2] - carried_offset
        return (float(dock_xy[0]), float(dock_xy[1]), float(self.scene.base_pose[2]))

    def _update_navigation(self) -> None:
        if self._navigation_waypoint >= len(self._navigation_path):
            self._finish_navigation()
            return
        current = self.scene.base_pose.copy()
        target = np.asarray(
            self._navigation_path[self._navigation_waypoint], dtype=float
        )
        delta = target - current[:2]
        distance = float(np.linalg.norm(delta))
        step_distance = 0.003
        if distance <= step_distance:
            next_xy = target
            self._navigation_waypoint += 1
        else:
            next_xy = current[:2] + delta / distance * step_distance
        # The chassis is holonomic.  Keep the arm's world-facing base frame
        # fixed while translating; snapping yaw to every A* segment would
        # rotate the fixed-base articulation and shock the grasp joint.
        yaw = float(current[2])
        self.scene.set_mobile_base_pose((next_xy[0], next_xy[1], yaw))
        if self._navigation_waypoint >= len(self._navigation_path):
            self._finish_navigation()

    def _finish_navigation(self) -> None:
        destination = self._navigation_destination
        mode = self._navigation_mode
        dock = self._navigation_dock_pose or DOCKING_POSES[destination]
        self.scene.set_mobile_base_pose(dock)
        self._navigation_path = []
        self._navigation_waypoint = 0
        self._navigation_mode = ""
        self._navigation_destination = ""
        self._navigation_dock_pose = None
        self.state.phase = DemoPhase.DOCK
        self.state.robot_zone = destination.replace("_", " ")
        self.state.active_route = "docked"
        self.state.log(f"Docked at {destination}; refreshing the arm base frame.")
        if mode == "to_target":
            self._arrived_for_current_target = True
            self.controller = self._new_pick_place_controller()
            # The wrist may have reoriented a tilted object during lift and
            # navigation.  Re-read the physical offset instead of reusing the
            # pre-rotation grasp geometry for placement.  This must happen
            # after constructing RMPflow with the new mobile-base frame.
            object_position, _ = self._current_rigid.get_world_pose()
            control_position, _ = self._get_controlled_frame_pose()
            self._grasp_hand_offset = (
                control_position - np.asarray(object_position, dtype=float)
            )
            self.controller._event = 5
            self.controller._t = 0.0
            self.controller._current_target_x = float(object_position[0])
            self.controller._current_target_y = float(object_position[1])
            self._last_event = 4
        elif mode == "to_source":
            self.scene.robot.gripper.open()
            self.controller = self._new_pick_place_controller()
            self._last_event = -1
            self._settle_steps = 0
            self._release_wait_steps = 0
            self._grasp_contact_wait_steps = 0
            self._grasp_hand_offset = np.zeros(3)
            self._arrived_for_current_target = False
            self.state.active_target = self._current_target_zone
            self.state.log(
                f"Ready to pick {self._current_object_id} from "
                f"{destination.replace('_', ' ')}."
            )

    def inject_object_moved(self) -> None:
        if self._joint_active:
            self.state.log("The current object is held; use the grasp-drop injection instead.")
            return
        # Model an external bump by changing velocity.  The object then moves
        # and settles through PhysX; its pose is never teleported.
        self._current_rigid.set_linear_velocity(np.array([0.38, 0.32, 0.10]))
        self._current_rigid.set_angular_velocity(np.array([0.0, 0.0, 1.4]))
        self.state.log(
            f"Anomaly: an external impulse moved {self._current_object_id}; waiting to relocalize."
        )
        self._remember(
            f"object_moved:{self._current_object_id}",
            {"cause": "external_impulse"},
            "relocalize",
        )
        if self.state.status == "running":
            self.state.phase = DemoPhase.RECOVER
            self._reobserve_wait_steps = 120
            self._reobserve_reason = (
                f"{self._current_object_id} moved under an external impulse"
            )

    def inject_grasp_drop(self) -> None:
        if not self._joint_active:
            self.state.log("No active physical grasp; the drop event was ignored.")
            return
        self._remove_grasp_joint()
        self.scene.robot.gripper.open()
        self.state.holding = False
        self.state.phase = DemoPhase.RECOVER
        self.state.log(
            f"Anomaly: grasp constraint released; waiting for {self._current_object_id} to settle."
        )
        self._remember(
            f"grasp_lost:{self._current_object_id}",
            {"event": self._last_event},
            "secure_regrasp",
        )
        self._reobserve_wait_steps = 150
        self._reobserve_reason = "relocalize after a physically dropped grasp"

    def inject_target_occupied(self) -> None:
        blocker = self.scene.stage.GetPrimAtPath("/World/Home/Task/PrimaryPlateBlocker")
        if blocker.IsValid():
            blocker.SetActive(True)
        if self._current_target_zone != "care_station":
            self.state.log(
                "Care target is occupied; the planner recorded it for the next care delivery."
            )
            self._remember(
                "target_occupied:care_station", {}, "stage_at_buffer_then_clear"
            )
            return
        task = TASK_BY_ID[self._current_object_id]
        self._active_place_position = np.array(
            [0.90, 2.85, TABLE_TOP_Z + 0.024 + task.half_height + 0.002],
            dtype=float,
        )
        self._current_target_zone = "buffer_tray"
        self._target_support_path = BUFFER_PLATE_COLLIDER_PATH
        self._staging_due_to_occupancy = True
        self._arrived_for_current_target = False
        self.state.active_target = "buffer tray (temporary staging)"
        self.state.revision += 1
        self.state.log(
            "Anomaly: care slot is physically occupied; staging the item on the buffer tray."
        )
        self._remember(
            "target_occupied:care_station", {}, "stage_at_buffer_then_clear"
        )
        if self._navigation_mode:
            self._begin_navigation("buffer_tray", mode="to_target")

    def inject_path_blocked(self, corridor: str = "corridor_low") -> None:
        if corridor not in DYNAMIC_CORRIDOR_OBSTACLES:
            raise ValueError(f"Unknown corridor: {corridor}")
        obstacle = self.scene.stage.GetPrimAtPath(DYNAMIC_OBSTACLE_PATH)
        if obstacle.IsValid():
            obstacle.SetActive(True)
            rectangle = DYNAMIC_CORRIDOR_OBSTACLES[corridor]
            center_y = (rectangle[1] + rectangle[3]) * 0.5
            ops = UsdGeom.Xformable(obstacle).GetOrderedXformOps()
            if ops:
                ops[0].Set(Gf.Vec3d(0.0, center_y, 0.42))
        self._blocked_corridors.add(corridor)
        self.state.revision += 1
        self.state.log(
            f"Anomaly: a collidable obstacle blocks {corridor}; stopping and replanning."
        )
        self._remember(
            f"path_blocked:{self._current_target_zone}",
            {"blocked_corridors": sorted(self._blocked_corridors)},
            "stop_refresh_astar_alternate_route",
        )
        if self._navigation_mode:
            destination = self._navigation_destination
            mode = self._navigation_mode
            self._begin_navigation(destination, mode=mode)

    def _restart_from_observation(self, reason: str) -> None:
        self._remove_grasp_joint()
        self._navigation_path = []
        self._navigation_waypoint = 0
        self._navigation_mode = ""
        self._navigation_destination = ""
        self._navigation_dock_pose = None
        self._arrived_for_current_target = False
        position, _ = self._current_rigid.get_world_pose()
        if position[2] < 0.03:
            self.state.status = "failed"
            self.state.phase = DemoPhase.FAILED
            self.state.last_error = (
                f"{self._current_object_id} left the mapped room; operator recovery required"
            )
            self.state.log(self.state.last_error)
            return
        # A failed close action remains the articulation drive target until it
        # is explicitly replaced.  Every recovery therefore starts by opening
        # the physical fingers, giving the approach phase real clearance.
        self.scene.robot.gripper.open()
        self.controller.reset(end_effector_initial_height=1.26)
        self._last_event = -1
        self._settle_steps = 0
        self._release_wait_steps = 0
        self._grasp_contact_wait_steps = 0
        self._grasp_hand_offset = np.zeros(3)
        self.state.status = "running"
        self.state.phase = DemoPhase.RECOVER
        self.state.revision += 1
        self.state.progress = 0.06
        self.state.log(f"Plan r{self.state.revision}: {reason}; using the latest PhysX pose.")

    def _read_contact_bodies(self) -> tuple[set[str], float]:
        bodies: set[str] = set()
        total_impulse = 0.0
        try:
            records = self._contact_interface.get_rigid_body_raw_data(
                self._current_object_path
            )
        except Exception:
            return bodies, total_impulse
        for record in records:
            for key in ("body0", "body1"):
                decoded = self._contact_interface.decode_body_name(record[key])
                if decoded:
                    bodies.add(str(decoded))
            impulse = record["impulse"]
            total_impulse += float(
                np.linalg.norm([impulse["x"], impulse["y"], impulse["z"]])
            )
        return bodies, total_impulse

    @staticmethod
    def _contains_body(bodies: set[str], path: str) -> bool:
        return any(path in body or body in path for body in bodies)

    def _refresh_contact_state(self) -> tuple[set[str], float]:
        bodies, impulse = self._read_contact_bodies()
        self._last_contact_bodies = bodies
        self.state.left_finger_contact = self._contains_body(bodies, LEFT_FINGER_PATH)
        self.state.right_finger_contact = self._contains_body(bodies, RIGHT_FINGER_PATH)
        if self._contains_body(bodies, CARE_CUP_COLLIDER_PATH):
            self.state.support_contact = "care cup slot"
        elif self._contains_body(bodies, CARE_MEDICINE_COLLIDER_PATH):
            self.state.support_contact = "care medicine slot"
        elif self._contains_body(bodies, BUFFER_PLATE_COLLIDER_PATH):
            self.state.support_contact = "buffer tray"
        elif self._contains_body(bodies, STORAGE_COLLIDER_PATH):
            self.state.support_contact = "storage bin"
        elif self._contains_body(bodies, LIVING_TABLE_COLLIDER_PATH):
            self.state.support_contact = "living table"
        else:
            self.state.support_contact = "none"
        self.state.contact_impulse = impulse
        return bodies, impulse

    def _try_create_physical_grasp(self) -> Optional[bool]:
        bodies, _ = self._refresh_contact_state()
        has_left = self._contains_body(bodies, LEFT_FINGER_PATH)
        has_right = self._contains_body(bodies, RIGHT_FINGER_PATH)
        if not (has_left and has_right):
            self._grasp_contact_wait_steps += 1
            if self._grasp_contact_wait_steps == 1:
                self.state.phase = DemoPhase.GRASP
                self.state.log(
                    f"Contact gate: waiting for both Franka fingers to touch {self._current_object_id}."
                )
            if self._grasp_contact_wait_steps in (1, 60, 120, 180):
                mug_position, _ = self._current_rigid.get_world_pose()
                left_position, _ = get_world_pose(LEFT_FINGER_PATH)
                right_position, _ = get_world_pose(RIGHT_FINGER_PATH)
                control_position = self._get_controlled_frame_position()
                finger_joints = self.scene.robot.gripper.get_joint_positions()
                self.state.log(
                    "Grasp diagnostic %d: mug=%s control=%s left=%s right=%s "
                    "finger_q=%s contacts=%s"
                    % (
                        self._grasp_contact_wait_steps,
                        np.round(mug_position, 3).tolist(),
                        np.round(control_position, 3).tolist(),
                        np.round(left_position, 3).tolist(),
                        np.round(right_position, 3).tolist(),
                        np.round(finger_joints, 4).tolist(),
                        sorted(bodies),
                    )
                )
            if self._grasp_contact_wait_steps <= self.MAX_CONTACT_WAIT_STEPS:
                return None
            self.state.last_error = (
                "Grasp rejected: PhysX did not report simultaneous left/right finger contact"
            )
            return False

        hand_position, hand_orientation = get_world_pose(self.HAND_PATH)
        mug_position, mug_orientation = self._current_rigid.get_world_pose()
        hand_distance = float(np.linalg.norm(hand_position - np.asarray(mug_position)))
        left_position, _ = get_world_pose(LEFT_FINGER_PATH)
        right_position, _ = get_world_pose(RIGHT_FINGER_PATH)
        left_distance = float(np.linalg.norm(left_position - np.asarray(mug_position)))
        right_distance = float(np.linalg.norm(right_position - np.asarray(mug_position)))
        if hand_distance > 0.14 or max(left_distance, right_distance) > 0.11:
            self.state.last_error = (
                "Grasp rejected: contact paths were reported outside the validated grasp envelope"
            )
            return False

        stage = self.scene.stage
        if stage.GetPrimAtPath(self.JOINT_PATH).IsValid():
            stage.RemovePrim(self.JOINT_PATH)
        hand_world = tf_matrix_from_pose(hand_position, hand_orientation)
        mug_world = tf_matrix_from_pose(mug_position, mug_orientation)
        relative = np.linalg.inv(hand_world) @ mug_world
        local_position, local_orientation = pose_from_tf_matrix(relative)

        joint = UsdPhysics.FixedJoint.Define(stage, self.JOINT_PATH)
        joint.CreateBody0Rel().SetTargets([Sdf.Path(self.HAND_PATH)])
        joint.CreateBody1Rel().SetTargets([Sdf.Path(self._current_object_path)])
        joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*map(float, local_position)))
        joint.CreateLocalRot0Attr().Set(Gf.Quatf(*map(float, local_orientation)))
        joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
        joint.CreateLocalRot1Attr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
        joint.CreateCollisionEnabledAttr().Set(False)
        # The injected drop removes this joint explicitly.  These thresholds
        # are deliberately above normal Franka transfer loads so an ordinary
        # lift cannot masquerade as a requested drop anomaly.
        joint.CreateBreakForceAttr().Set(5000.0)
        joint.CreateBreakTorqueAttr().Set(500.0)

        self._attachment_relative_transform = relative
        # M = H * relative.  Preserve the object's observed yaw and only remove
        # roll/pitch for items that must stay upright.  This yields a nearby,
        # reachable wrist orientation instead of needlessly spinning a mug
        # around its vertical axis after contact.
        object_rotation = quat_to_rot_matrix(np.asarray(mug_orientation))
        if TASK_BY_ID[self._current_object_id].keep_upright:
            yaw = float(np.arctan2(object_rotation[1, 0], object_rotation[0, 0]))
            desired_object_rotation = quat_to_rot_matrix(
                euler_angles_to_quat(np.array([0.0, 0.0, yaw]))
            )
        else:
            desired_object_rotation = object_rotation
        control_position, control_rotation = self._get_controlled_frame_pose()
        control_world = np.eye(4)
        control_world[:3, :3] = control_rotation
        control_world[:3, 3] = control_position
        control_relative = np.linalg.inv(control_world) @ mug_world
        desired_control_rotation = (
            desired_object_rotation @ control_relative[:3, :3].T
        )
        self._transport_hand_orientation = rot_matrix_to_quat(
            desired_control_rotation
        )
        self._joint_age_steps = 0
        self._grasp_hand_offset = control_position - np.asarray(mug_position)
        self._joint_active = True
        self.state.holding = True
        self.state.attachment_mode = "PhysX fixed joint"
        self.state.log(
            "Dual-finger contact confirmed; created a pose-preserving PhysX FixedJoint."
        )
        return True

    def _attachment_is_continuous(self, *, tolerance: float = 0.025) -> bool:
        prim = self.scene.stage.GetPrimAtPath(self.JOINT_PATH)
        if not prim.IsValid():
            return False
        hand_position, hand_orientation = get_world_pose(self.HAND_PATH)
        mug_position, mug_orientation = self._current_rigid.get_world_pose()
        current_relative = np.linalg.inv(
            tf_matrix_from_pose(hand_position, hand_orientation)
        ) @ tf_matrix_from_pose(mug_position, mug_orientation)
        translation_error = float(
            np.linalg.norm(
                current_relative[:3, 3] - self._attachment_relative_transform[:3, 3]
            )
        )
        return translation_error <= tolerance

    def _remove_grasp_joint(self) -> None:
        prim = self.scene.stage.GetPrimAtPath(self.JOINT_PATH)
        if prim.IsValid():
            self.scene.stage.RemovePrim(self.JOINT_PATH)
        self._joint_active = False
        self._joint_age_steps = 0
        self.state.attachment_mode = "none"

    def _handle_lost_attachment(self, reason: str) -> None:
        self._remove_grasp_joint()
        self.state.holding = False
        self.state.phase = DemoPhase.RECOVER
        self.state.log("Post-action verification failed: " + reason)
        self._remember(
            f"grasp_lost:{self._current_object_id}",
            {"event": self._last_event},
            "secure_regrasp",
        )
        self._reobserve_wait_steps = 150
        self._reobserve_reason = reason

    def _get_controlled_frame_pose(self) -> tuple[np.ndarray, np.ndarray]:
        cspace = self.controller._cspace_controller
        active_subset = cspace.articulation_rmp.get_active_joints_subset()
        active_positions = np.asarray(active_subset.get_joint_positions(), dtype=float)
        position, rotation = cspace.rmp_flow.get_end_effector_pose(active_positions)
        return np.asarray(position, dtype=float), np.asarray(rotation, dtype=float)

    def _get_controlled_frame_position(self) -> np.ndarray:
        return self._get_controlled_frame_pose()[0]

    def _verify_result(self) -> None:
        bodies, _ = self._refresh_contact_state()
        position, orientation = self._current_rigid.get_world_pose()
        position = np.asarray(position, dtype=float)
        orientation = np.asarray(orientation, dtype=float)
        xy_error = float(np.linalg.norm(position[:2] - self._active_place_position[:2]))
        up = quat_to_rot_matrix(orientation)[:, 2]
        upright = float(np.dot(up, np.array([0.0, 0.0, 1.0])))
        linear_speed = float(np.linalg.norm(self._current_rigid.get_linear_velocity()))
        angular_speed = float(np.linalg.norm(self._current_rigid.get_angular_velocity()))
        expected_support = self._target_support_path
        support_contact = self._contains_body(bodies, expected_support)
        stable_height = abs(position[2] - self._active_place_position[2]) <= 0.035
        no_gripper_contact = not (
            self._contains_body(bodies, LEFT_FINGER_PATH)
            or self._contains_body(bodies, RIGHT_FINGER_PATH)
        )
        passed = (
            xy_error <= 0.06
            and (
                not TASK_BY_ID[self._current_object_id].keep_upright
                or upright >= 0.90
            )
            and stable_height
            and linear_speed <= 0.05
            and angular_speed <= 0.20
            and support_contact
            and no_gripper_contact
            and not self._joint_active
        )
        if passed:
            self.state.last_error = None
            self.state.physics_verified = True
            self.state.log(
                f"Verified dynamic placement: error {xy_error:.3f} m, upright {upright:.3f}, "
                f"speed {linear_speed:.3f} m/s, support contact YES."
            )
            signature_prefix = (
                "task_staged" if self._staging_due_to_occupancy else "task_complete"
            )
            self._remember(
                f"{signature_prefix}:{self._current_object_id}_to_{self._current_target_zone}",
                {
                    "xy_error": xy_error,
                    "upright": upright,
                    "linear_speed": linear_speed,
                    "support_contact": True,
                },
                "verified_physics",
            )
            if self._staging_due_to_occupancy:
                self._resume_after_buffer_staging()
            else:
                self._complete_current_object()
        else:
            self._fail_and_recover(
                "Final physics verification failed: "
                f"xy={xy_error:.3f}, upright={upright:.3f}, linear={linear_speed:.3f}, "
                f"angular={angular_speed:.3f}, support={support_contact}, "
                f"gripper_clear={no_gripper_contact}"
            )

    def _resume_after_buffer_staging(self) -> None:
        blocker = self.scene.stage.GetPrimAtPath(
            "/World/Home/Task/PrimaryPlateBlocker"
        )
        if blocker.IsValid():
            blocker.SetActive(False)
        task = TASK_BY_ID[self._current_object_id]
        self._current_target_zone = task.target_zone
        self._active_place_position = np.array(task.target_position, dtype=float)
        self._target_support_path = {
            "cup": CARE_CUP_COLLIDER_PATH,
            "medicine_box": CARE_MEDICINE_COLLIDER_PATH,
        }[self._current_object_id]
        self._staging_due_to_occupancy = False
        self._arrived_for_current_target = False
        self.state.revision += 1
        self.state.active_target = self._current_target_zone
        self.state.physics_verified = False
        self.state.log(
            "Buffer placement verified; occupancy condition cleared, now resuming the original care goal."
        )
        self.scene.robot.gripper.open()
        self.controller = self._new_pick_place_controller()
        self._last_event = -1
        self._settle_steps = 0
        self._release_wait_steps = 0
        self._grasp_contact_wait_steps = 0
        self._grasp_hand_offset = np.zeros(3)

    def _complete_current_object(self) -> None:
        if self._current_object_id not in self.state.completed_objects:
            self.state.completed_objects.append(self._current_object_id)
        self.state.log(
            f"Subgoal complete: {self._current_object_id} is physically verified in "
            f"{self._current_target_zone} ({len(self.state.completed_objects)}/{len(OBJECT_TASKS)})."
        )
        self._retry_count = 0
        if self._task_index + 1 >= len(OBJECT_TASKS):
            self.state.status = "completed"
            self.state.phase = DemoPhase.COMPLETED
            self.state.progress = 1.0
            self.state.active_route = "mission complete"
            self.state.log(
                "All household goals verified: care delivery and toy storage are complete."
            )
            self._remember(
                "mission_complete:home_care_and_tidy",
                {"objects": list(self.state.completed_objects)},
                "verified_multi_zone_mission",
            )
            return

        self._task_index += 1
        self._select_task(self._task_index)
        self._arrived_for_current_target = False
        self.state.physics_verified = False
        self._begin_navigation("living_table", mode="to_source")

    def _fail_and_recover(self, reason: str) -> None:
        self.state.last_error = reason
        self.state.phase = DemoPhase.RECOVER
        self.state.log("Post-action verification failed: " + reason)
        self._retry_count += 1
        if self._retry_count >= 4:
            self.state.status = "failed"
            self.state.phase = DemoPhase.FAILED
            self.state.log("Safe retry limit reached; the robot has stopped.")
            return
        self._restart_from_observation(reason)

    def _remember(self, signature: str, context: dict, repair: str) -> None:
        self.memory.record(
            MemoryEpisode(
                signature=signature,
                context=context,
                repair={"strategy": repair, "backend": "Isaac Sim 5.1 PhysX"},
                outcome="recorded",
                task_id=f"isaac-home-{self._run_id}",
            )
        )
        self.state.memory_episodes = self.memory.count()

    def close(self) -> None:
        self._remove_grasp_joint()
        self.memory.close()

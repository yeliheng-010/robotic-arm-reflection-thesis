"""Executable entry point for the native Isaac Sim home demonstration."""

from __future__ import annotations

import argparse
import os
import traceback
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from .assets import ASSET_ROOT_DEFAULT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Isaac Sim native future embodied AI demo")
    parser.add_argument("--headless", action="store_true", help="run physics verification without a window")
    parser.add_argument("--auto-start", action="store_true", help="start the household mission after loading")
    parser.add_argument(
        "--showcase",
        action="store_true",
        help="run the full mission and automatically demonstrate live route replanning",
    )
    parser.add_argument("--max-steps", type=int, default=0, help="stop after this many simulation steps")
    parser.add_argument(
        "--memory",
        default="logs/isaac_future_ai_memory.sqlite3",
        help="SQLite long-term memory path",
    )
    parser.add_argument(
        "--asset-root",
        default=ASSET_ROOT_DEFAULT,
        help="Isaac Sim 5.1 asset root URL or local mirror",
    )
    parser.add_argument("--save-stage", default="", help="optionally export the composed USD stage")
    parser.add_argument(
        "--inject-move-step",
        type=int,
        default=0,
        help="headless regression: bump the current object at this simulation step",
    )
    parser.add_argument(
        "--inject-drop-step",
        type=int,
        default=0,
        help="headless regression: drop the active grasp at this simulation step",
    )
    parser.add_argument(
        "--inject-occupied-step",
        type=int,
        default=0,
        help="headless regression: occupy the current care slot at this simulation step",
    )
    parser.add_argument(
        "--inject-block-step",
        type=int,
        default=0,
        help="headless regression: block the currently preferred lower corridor",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        raise SystemExit(
            "NVIDIA Omniverse EULA acceptance is required. Run with OMNI_KIT_ACCEPT_EULA=YES."
        )

    from isaacsim import SimulationApp

    simulation_app = SimulationApp(
        {
            "headless": args.headless,
            "renderer": "RaytracedLighting",
            "anti_aliasing": 3,
            "width": 1600,
            "height": 900,
            "enable_crashreporter": False,
            "limit_cpu_threads": 16,
            "extra_args": ["--/telemetry/enableAnonymousData=false"],
        }
    )

    from .controller import HomeTaskController
    from .scene import build_home_scene
    from .state import DemoState

    scene = None
    controller = None
    panel = None
    try:
        state = DemoState()
        scene = build_home_scene(simulation_app, args.asset_root)
        controller = HomeTaskController(scene, state, Path(args.memory))
        if not args.headless:
            from .ui import NativeControlPanel

            panel = NativeControlPanel(state)

        if args.save_stage:
            export_path = Path(args.save_stage).expanduser().resolve()
            export_path.parent.mkdir(parents=True, exist_ok=True)
            scene.stage.GetRootLayer().Export(str(export_path))
            state.log(f"Composed stage exported to {export_path}")

        showcase_armed = bool(args.showcase)
        showcase_blocked = False
        if args.auto_start or args.showcase or args.headless:
            controller.start()
        if args.showcase:
            state.showcase_mode = True
            state.showcase_event = "waiting to create a live corridor obstacle"
            state.log(
                "Adaptive showcase armed: the first transport will face a new physical obstacle."
            )

        step = 0
        while simulation_app.is_running():
            if args.inject_move_step and step == args.inject_move_step:
                controller.inject_object_moved()
            if args.inject_drop_step and step == args.inject_drop_step:
                controller.inject_grasp_drop()
            if args.inject_occupied_step and step == args.inject_occupied_step:
                controller.inject_target_occupied()
            if args.inject_block_step and step == args.inject_block_step:
                controller.inject_path_blocked("corridor_low")

            if (
                showcase_armed
                and not showcase_blocked
                and state.status == "running"
                and state.current_object == "cup"
                and state.holding
                and state.active_route == "lower corridor"
            ):
                controller.inject_path_blocked("corridor_low")
                showcase_blocked = True
                state.showcase_event = "lower route blocked; A* replanned in orange"

            if panel is not None:
                command = panel.pop_command()
                while command is not None:
                    if command == "start":
                        showcase_armed = False
                        showcase_blocked = False
                        state.showcase_mode = False
                        state.showcase_event = "manual full mission"
                        controller.start()
                    elif command == "showcase":
                        if state.status != "idle":
                            controller.reset()
                        showcase_armed = True
                        showcase_blocked = False
                        state.showcase_mode = True
                        state.showcase_event = (
                            "waiting to create a live corridor obstacle"
                        )
                        controller.start()
                        state.log(
                            "Adaptive showcase armed: the first transport will face a new physical obstacle."
                        )
                    elif command == "reset":
                        showcase_armed = False
                        showcase_blocked = False
                        controller.reset()
                    elif command == "move_mug":
                        controller.inject_object_moved()
                    elif command == "drop":
                        controller.inject_grasp_drop()
                    elif command == "occupy_target":
                        controller.inject_target_occupied()
                    elif command == "block_route":
                        controller.inject_path_blocked("corridor_low")
                    command = panel.pop_command()

            controller.update()
            # GUI mode renders every step; headless regression spends its time
            # on PhysX only so closed-loop checks finish quickly.
            scene.world.step(render=not args.headless)
            if panel is not None:
                panel.refresh()

            step += 1
            if args.max_steps and step >= args.max_steps:
                break
            if args.headless and state.status in ("completed", "failed"):
                break

        mug_position, mug_orientation = scene.mug.get_world_pose()
        mug_linear_velocity = scene.mug.get_linear_velocity()
        mug_angular_velocity = scene.mug.get_angular_velocity()
        hand_position, _ = scene.robot.end_effector.get_world_pose()
        control_position = controller._get_controlled_frame_position()
        object_states = {}
        for object_id, rigid in scene.objects.items():
            object_position, object_orientation = rigid.get_world_pose()
            object_states[object_id] = {
                "position": [round(float(value), 4) for value in object_position],
                "orientation": [
                    round(float(value), 4) for value in object_orientation
                ],
                "linear_speed": round(
                    float(np.linalg.norm(rigid.get_linear_velocity())),
                    5,
                ),
            }
        print(
            "ISAAC_DEMO_RESULT",
            {
                "status": state.status,
                "phase": state.phase.value,
                "revision": state.revision,
                "target": state.active_target,
                "current_object": state.current_object,
                "completed_objects": list(state.completed_objects),
                "robot_zone": state.robot_zone,
                "active_route": state.active_route,
                "base_pose": [
                    round(float(value), 4) for value in scene.base_pose
                ],
                "objects": object_states,
                "holding": state.holding,
                "left_finger_contact": state.left_finger_contact,
                "right_finger_contact": state.right_finger_contact,
                "support_contact": state.support_contact,
                "attachment_mode": state.attachment_mode,
                "physics_verified": state.physics_verified,
                "last_error": state.last_error,
                "mug_position": [round(float(value), 4) for value in mug_position],
                "mug_orientation": [
                    round(float(value), 4) for value in mug_orientation
                ],
                "mug_linear_velocity": [
                    round(float(value), 4) for value in mug_linear_velocity
                ],
                "mug_angular_velocity": [
                    round(float(value), 4) for value in mug_angular_velocity
                ],
                "hand_position": [round(float(value), 4) for value in hand_position],
                "control_position": [
                    round(float(value), 4) for value in control_position
                ],
                "place_position": [
                    round(float(value), 4) for value in controller._active_place_position
                ],
                "grasp_offset": [
                    round(float(value), 4) for value in controller._grasp_hand_offset
                ],
                "release_wait_steps": controller._release_wait_steps,
                "contact_wait_steps": controller._grasp_contact_wait_steps,
                "current_event": controller.controller.get_current_event(),
                "contact_bodies": sorted(controller._last_contact_bodies),
                "event_diagnostics": controller._event_diagnostics[-12:],
                "logs": state.log_lines(),
                "steps": step,
            },
            flush=True,
        )
        return 0 if state.status != "failed" else 1
    except Exception:
        # SimulationApp.close() can terminate Kit before Python's default
        # exception hook writes the traceback.  Emit it while Kit is still
        # alive so headless physics regressions never fail silently.
        traceback.print_exc()
        return 2
    finally:
        if controller is not None:
            controller.close()
        if scene is not None:
            scene.world.stop()
        simulation_app.close()


if __name__ == "__main__":
    raise SystemExit(main())

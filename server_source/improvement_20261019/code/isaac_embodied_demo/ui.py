"""Native omni.ui control panel; this is not a browser dashboard."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque

import omni.ui as ui

from .state import DemoState


class NativeControlPanel:
    def __init__(self, state: DemoState) -> None:
        self.state = state
        self.commands: Deque[str] = deque()
        self.window = ui.Window(
            "Future AI | Home Embodied Intelligence",
            width=390,
            height=760,
            dockPreference=ui.DockPreference.RIGHT_TOP,
        )
        self.window.deferred_dock_in(
            "Viewport", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE
        )
        asyncio.ensure_future(self._dock_to_viewport())
        with self.window.frame:
            with ui.VStack(spacing=8, height=0):
                ui.Label(
                    "Isaac Sim 5.1 Native Simulation",
                    height=32,
                    style={"font_size": 22, "color": 0xFFF3C47A},
                )
                ui.Label(
                    "RTX | PhysX | Mobile Franka | NVIDIA ArchViz Residential",
                    word_wrap=True,
                    style={"color": 0xFFB8C7D9},
                )
                ui.Separator(height=6)
                with ui.HStack(height=38, spacing=6):
                    ui.Button(
                        "Run Full Mission",
                        clicked_fn=lambda: self.commands.append("start"),
                    )
                    ui.Button(
                        "Adaptive Showcase",
                        clicked_fn=lambda: self.commands.append("showcase"),
                    )
                ui.Button(
                    "Reset Scene (memory retained)",
                    height=34,
                    clicked_fn=lambda: self.commands.append("reset"),
                )
                with ui.HStack(height=38, spacing=6):
                    ui.Button(
                        "Move Current Object",
                        clicked_fn=lambda: self.commands.append("move_mug"),
                    )
                    ui.Button(
                        "Inject Drop",
                        clicked_fn=lambda: self.commands.append("drop"),
                    )
                with ui.HStack(height=38, spacing=6):
                    ui.Button(
                        "Block Lower Route",
                        clicked_fn=lambda: self.commands.append("block_route"),
                    )
                    ui.Button(
                        "Occupy Care Slot",
                        clicked_fn=lambda: self.commands.append("occupy_target"),
                    )
                ui.Separator(height=6)
                self.status_label = ui.Label("", word_wrap=True, height=32)
                self.phase_label = ui.Label("", word_wrap=True, height=54)
                self.target_label = ui.Label("", word_wrap=True, height=28)
                self.mission_label = ui.Label("", word_wrap=True, height=44)
                self.physics_label = ui.Label("", word_wrap=True, height=48)
                self.showcase_label = ui.Label("", word_wrap=True, height=42)
                self.progress = ui.ProgressBar(height=18)
                ui.Separator(height=6)
                ui.Label(
                    "Household Mission (not a single-cup demo)",
                    style={"font_size": 18, "color": 0xFFE0E8F2},
                )
                self.plan_label = ui.Label(
                    "",
                    word_wrap=True,
                    height=126,
                    style={"color": 0xFFC8D6E5},
                )
                ui.Label(
                    "Events and Long-Term Memory",
                    style={"font_size": 18, "color": 0xFFE0E8F2},
                )
                self.log_label = ui.Label("", word_wrap=True, height=230)
                ui.Spacer()
                ui.Label(
                    "No foundation-model API is connected.\n"
                    "Simulation and UI both run inside Isaac Sim.",
                    word_wrap=True,
                    style={"color": 0xFF7F93A9},
                )
        self.refresh()

    async def _dock_to_viewport(self) -> None:
        # Kit creates its default dockspace asynchronously.  Waiting a few
        # update ticks mirrors NVIDIA's own setup-wizard implementation.
        import omni.kit.app

        for _ in range(4):
            await omni.kit.app.get_app().next_update_async()
        viewport = ui.Workspace.get_window("Viewport")
        if viewport is not None:
            self.window.dock_in(viewport, ui.DockPosition.RIGHT)

    def pop_command(self):
        return self.commands.popleft() if self.commands else None

    def refresh(self) -> None:
        status_map = {
            "idle": "IDLE",
            "running": "RUNNING",
            "completed": "COMPLETED",
            "failed": "STOPPED",
        }
        self.status_label.text = (
            f"System: {status_map.get(self.state.status, self.state.status)}  "
            f"Plan: r{self.state.revision}  "
            f"Holding: {'YES' if self.state.holding else 'NO'}"
        )
        self.phase_label.text = "Phase: " + self.state.phase_label
        self.target_label.text = "Target: " + self.state.active_target
        self.mission_label.text = (
            f"Object: {self.state.current_object}  Zone: {self.state.robot_zone}\n"
            f"Route: {self.state.active_route}  Completed: "
            f"{len(self.state.completed_objects)}/3"
        )
        self.physics_label.text = (
            "PhysX contacts: "
            f"L={'YES' if self.state.left_finger_contact else 'NO'}  "
            f"R={'YES' if self.state.right_finger_contact else 'NO'}  "
            f"Support={self.state.support_contact}\n"
            f"Attachment: {self.state.attachment_mode}  "
            f"Verified={'YES' if self.state.physics_verified else 'NO'}"
        )
        mode = "ADAPTIVE SHOWCASE" if self.state.showcase_mode else "FULL MISSION"
        self.showcase_label.text = (
            f"Mode: {mode}\n"
            f"Adaptation: {self.state.showcase_event} | Memory: "
            f"{self.state.memory_episodes} episodes"
        )
        completed = set(self.state.completed_objects)
        active = self.state.current_object if self.state.status == "running" else ""

        def task_line(object_id: str, label: str) -> str:
            if object_id in completed:
                marker = "[DONE]"
            elif object_id == active:
                marker = "[NOW ]"
            else:
                marker = "[NEXT]"
            return f"{marker} {label}"

        self.plan_label.text = "\n".join(
            (
                task_line("cup", "Cup -> care station (upright)"),
                task_line("medicine_box", "Medicine -> care station"),
                task_line("toy", "Toy -> physical storage bin"),
                "Live A* path: CYAN | replanned path: ORANGE",
                "Every placement requires PhysX contact verification",
            )
        )
        self.progress.model.set_value(float(self.state.progress))
        lines = self.state.log_lines()
        self.log_label.text = "\n".join(lines[-9:]) if lines else "No events"

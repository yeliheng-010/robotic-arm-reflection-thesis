from __future__ import annotations

import queue
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import glfw
import mujoco
import mujoco.viewer
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .engine import DemoEngine
from .simulator import MobileHomeSimulator


DEFAULT_INSTRUCTION = (
    "把客厅桌上的水杯和药盒送到照护区，"
    "把玩具放进收纳箱，并保持水杯直立"
)

FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")

COLORS = {
    "background": (8, 18, 29),
    "panel": (13, 31, 45),
    "line": (31, 58, 78),
    "text": (232, 241, 247),
    "muted": (137, 163, 181),
    "cyan": (70, 217, 230),
    "green": (102, 227, 159),
    "amber": (255, 196, 92),
    "red": (255, 111, 113),
}


def _font(size: int, *, bold: bool = False):
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError:
        return ImageFont.load_default()


def _fit_lines(draw: ImageDraw.ImageDraw, value: str, font, width: int) -> List[str]:
    lines: List[str] = []
    current = ""
    for character in value:
        candidate = current + character
        if current and draw.textlength(candidate, font=font) > width:
            lines.append(current)
            current = character
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render_native_hud(
    state: Dict[str, object],
    *,
    width: int = 430,
    height: int = 760,
    notice: str = "",
) -> np.ndarray:
    """Render a Chinese control/status panel for MuJoCo ``set_images``."""
    image = Image.new("RGB", (width, height), COLORS["background"])
    draw = ImageDraw.Draw(image)
    title_font = _font(24, bold=True)
    body_font = _font(15)
    body_bold = _font(15, bold=True)
    small_font = _font(12)
    tiny_font = _font(11)
    x = 20

    draw.text((x, 18), "未来具身智能", font=title_font, fill=COLORS["text"])
    draw.text((x, 51), "MUJOCO NATIVE EXPERIMENT", font=small_font, fill=COLORS["cyan"])
    draw.rounded_rectangle((260, 18, width - 18, 48), radius=14, outline=(39, 111, 123), fill=(11, 45, 57))
    draw.text((278, 25), "离线 · 无 API", font=small_font, fill=COLORS["cyan"])
    draw.line((18, 76, width - 18, 76), fill=COLORS["line"], width=1)

    status = str(state.get("status", "idle"))
    status_colors = {
        "running": COLORS["amber"],
        "completed": COLORS["green"],
        "failed": COLORS["red"],
        "stopped": COLORS["red"],
    }
    color = status_colors.get(status, COLORS["muted"])
    draw.ellipse((x, 94, x + 11, 105), fill=color)
    draw.text((x + 20, 88), status.upper(), font=body_bold, fill=color)
    draw.text(
        (190, 88),
        f"WORLD v{state['world']['version']}   PLAN r{state.get('revision', 0)}",
        font=small_font,
        fill=COLORS["muted"],
    )

    draw.rounded_rectangle((18, 125, width - 18, 226), radius=12, fill=COLORS["panel"], outline=COLORS["line"])
    draw.text((x + 10, 137), "当前目标", font=small_font, fill=COLORS["muted"])
    goal = state.get("goal") or {}
    instruction = str(goal.get("instruction") or "按 Enter 启动默认家庭整理任务")
    for index, line in enumerate(_fit_lines(draw, instruction, body_font, width - 70)[:3]):
        draw.text((x + 10, 161 + index * 23), line, font=body_font, fill=COLORS["text"])

    current = state.get("current_step") or {}
    draw.text((x, 247), "正在执行", font=small_font, fill=COLORS["muted"])
    current_text = str(current.get("explanation") or "等待任务")
    draw.text((x, 270), current_text[:24], font=body_bold, fill=COLORS["cyan"])

    plan = list(state.get("plan") or [])
    draw.text((x, 307), f"技能计划 · 剩余 {len(plan)} 步", font=small_font, fill=COLORS["muted"])
    plan_y = 334
    for index, step in enumerate(plan[:5]):
        running = index == 0 and status == "running"
        step_color = COLORS["amber"] if running else COLORS["text"]
        draw.ellipse((x, plan_y + 4, x + 19, plan_y + 23), outline=step_color, width=1)
        draw.text((x + 6, plan_y + 5), str(index + 1), font=tiny_font, fill=step_color)
        draw.text((x + 31, plan_y), str(step.get("explanation", ""))[:23], font=body_font, fill=step_color)
        draw.text(
            (x + 31, plan_y + 22),
            f"{step.get('skill', '')} · {step.get('target') or ''}",
            font=tiny_font,
            fill=COLORS["muted"],
        )
        plan_y += 48
    if not plan:
        draw.text((x, plan_y), "没有待执行步骤", font=body_font, fill=COLORS["muted"])

    logs = list(state.get("logs") or [])
    event_y = 580
    draw.line((18, event_y - 12, width - 18, event_y - 12), fill=COLORS["line"])
    draw.text((x, event_y), "最近事件", font=small_font, fill=COLORS["muted"])
    event_y += 24
    event_colors = {
        "repair": COLORS["amber"],
        "replan": COLORS["amber"],
        "failure": COLORS["red"],
        "error": COLORS["red"],
        "success": COLORS["green"],
        "event": COLORS["cyan"],
    }
    for item in logs[-3:]:
        kind = str(item.get("kind", ""))
        draw.rectangle((x, event_y + 4, x + 3, event_y + 19), fill=event_colors.get(kind, COLORS["line"]))
        draw.text((x + 10, event_y), str(item.get("message", ""))[:28], font=small_font, fill=COLORS["text"])
        event_y += 24

    if notice:
        draw.rounded_rectangle((18, height - 91, width - 18, height - 57), radius=8, fill=(32, 49, 42), outline=(58, 111, 79))
        draw.text((x + 8, height - 84), notice[:30], font=small_font, fill=COLORS["green"])

    draw.line((18, height - 46, width - 18, height - 46), fill=COLORS["line"])
    controls = "Enter 开始   1 封路   2 移物   3 脱落   4 占位   R 重置   S 停止   H 隐藏"
    draw.text((x, height - 33), controls, font=tiny_font, fill=COLORS["muted"])
    return np.asarray(image)


class NativeViewerApp:
    def __init__(
        self,
        *,
        memory_path: str,
        realtime: bool = True,
        instruction: str = DEFAULT_INSTRUCTION,
    ) -> None:
        self.simulator = MobileHomeSimulator(realtime=realtime)
        self.engine = DemoEngine(simulator=self.simulator, memory_path=memory_path)
        self.instruction = instruction
        self._keys: "queue.Queue[int]" = queue.Queue()
        self._notice = ""
        self._notice_until = 0.0
        self._hud_visible = True
        self._last_hud_update = 0.0
        self._last_hud_size: Optional[Tuple[int, int]] = None

    def run(self) -> int:
        try:
            with mujoco.viewer.launch_passive(
                self.simulator.mj_model,
                self.simulator.mj_data,
                key_callback=self._on_key,
                show_left_ui=False,
                show_right_ui=False,
            ) as viewer:
                self.simulator.attach_viewer(viewer)
                viewer.cam.lookat[:] = (3.0, 2.0, 0.65)
                viewer.cam.azimuth = 142
                viewer.cam.elevation = -42
                viewer.cam.distance = 6.6
                self._set_notice("原生仿真已就绪，按 Enter 开始")
                # Populate the framebuffer once before querying its viewport.
                # Some desktop backends report a 0x0 viewport until the first
                # sync, which would otherwise postpone the HUD indefinitely.
                viewer.sync()
                self._update_hud(viewer)
                self._last_hud_update = time.monotonic()

                while viewer.is_running():
                    self._process_keys(viewer)
                    now = time.monotonic()
                    if self._hud_visible and now - self._last_hud_update >= 0.12:
                        self._update_hud(viewer)
                        self._last_hud_update = now
                    viewer.sync()
                    time.sleep(0.016)
                self.engine.stop()
                self.engine.wait(timeout=5.0)
                self.simulator.detach_viewer()
            return 0
        except KeyboardInterrupt:
            return 0
        finally:
            # Also clears a stale handle if the terminal interrupts while the
            # viewer context itself is unwinding.
            self.simulator.detach_viewer()
            self.engine.close()

    def _on_key(self, keycode: int) -> None:
        self._keys.put(keycode)

    def _process_keys(self, viewer) -> None:
        while True:
            try:
                key = self._keys.get_nowait()
            except queue.Empty:
                return
            try:
                if key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER):
                    if self.engine.status not in ("idle",):
                        self.engine.reset(in_place=True)
                    self.engine.start(self.instruction, background=True)
                    self._set_notice("家庭整理任务已经启动")
                elif key == glfw.KEY_1:
                    result = self.engine.inject_event("path_blocked", "corridor_high")
                    self._set_notice(str(result["message"]))
                elif key == glfw.KEY_2:
                    result = self.engine.inject_event("object_moved", "cup")
                    self._set_notice(str(result["message"]))
                elif key == glfw.KEY_3:
                    result = self.engine.inject_event("grasp_lost")
                    self._set_notice(str(result["message"]))
                elif key == glfw.KEY_4:
                    result = self.engine.inject_event("target_occupied", "care_station")
                    self._set_notice(str(result["message"]))
                elif key == glfw.KEY_5:
                    result = self.engine.inject_event("clear_obstacle")
                    self._set_notice(str(result["message"]))
                elif key == glfw.KEY_R:
                    self.engine.reset(in_place=True)
                    self._set_notice("场景已重置，长期记忆保留")
                elif key == glfw.KEY_S:
                    self.engine.stop()
                    self._set_notice("已请求安全停止")
                elif key == glfw.KEY_H:
                    self._hud_visible = not self._hud_visible
                    if not self._hud_visible:
                        viewer.clear_images()
                        viewer.clear_texts()
                    else:
                        self._last_hud_update = 0.0
            except Exception as exc:
                self._set_notice(f"操作未执行：{exc}")

    def _update_hud(self, viewer) -> None:
        viewport = viewer.viewport
        if viewport is None or viewport.width < 600 or viewport.height < 420:
            return
        panel_width = min(430, max(350, int(viewport.width * 0.34)))
        panel_height = min(760, viewport.height - 28)
        notice = self._notice if time.monotonic() < self._notice_until else ""
        panel = render_native_hud(
            self.engine.state(), width=panel_width, height=panel_height, notice=notice
        )
        rect = mujoco.MjrRect(
            viewport.width - panel_width - 14,
            max(14, viewport.height - panel_height - 14),
            panel_width,
            panel_height,
        )
        viewer.set_images((rect, panel))
        # Keep a native MuJoCo text line as an accessibility/fallback overlay;
        # the image above carries the full Chinese status and controls.
        viewer.set_texts(
            (
                mujoco.mjtFontScale.mjFONTSCALE_100,
                mujoco.mjtGridPos.mjGRID_BOTTOMLEFT,
                "FUTURE AI EMULATOR",
                "ENTER start | 1-5 events | R reset | S stop | H HUD",
            )
        )
        self._last_hud_size = (panel_width, panel_height)

    def _set_notice(self, message: str) -> None:
        self._notice = message
        self._notice_until = time.monotonic() + 3.5


__all__ = ["DEFAULT_INSTRUCTION", "NativeViewerApp", "render_native_hud"]

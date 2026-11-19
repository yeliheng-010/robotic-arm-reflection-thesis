from __future__ import annotations

import re
import uuid
from typing import Dict, Iterable, List, Sequence

from .models import GoalItem, GoalSpec


class UnsupportedInstruction(ValueError):
    pass


OBJECT_ALIASES: Dict[str, Sequence[str]] = {
    "cup": ("水杯", "杯子", "杯", "cup"),
    "medicine_box": ("药盒", "药品", "药", "medicine"),
    "toy": ("玩具", "积木", "toy"),
    "remote": ("遥控器", "remote"),
}

ZONE_ALIASES: Dict[str, Sequence[str]] = {
    "care_station": ("照护区", "照护台", "护理区", "床头", "care station"),
    "storage_bin": ("收纳箱", "玩具箱", "收纳区", "storage"),
    "living_table": ("客厅桌", "桌面", "原处", "living table"),
    "buffer_tray": ("临时托盘", "缓冲区", "buffer"),
}

DEFAULT_TARGETS = {
    "cup": "care_station",
    "medicine_box": "care_station",
    "toy": "storage_bin",
    "remote": "living_table",
}

SUPPORTED_ACTION_WORDS = ("整理", "收拾", "放", "送", "搬", "拿")


def _mentioned(text: str, aliases: Dict[str, Sequence[str]]) -> List[str]:
    hits = []
    for canonical, words in aliases.items():
        positions = [text.find(word.lower()) for word in words if word.lower() in text]
        if positions:
            hits.append((min(positions), canonical))
    return [canonical for _, canonical in sorted(hits)]


def _clause_target(clause: str) -> str | None:
    zones = _mentioned(clause, ZONE_ALIASES)
    return zones[-1] if zones else None


def parse_instruction(instruction: str) -> GoalSpec:
    """Parse the intentionally bounded Chinese command language.

    This parser is explicit about its limits.  It accepts paraphrases inside
    the implemented household domain and raises ``UnsupportedInstruction``
    instead of inventing objects or actions.
    """

    text = " ".join(instruction.strip().lower().split())
    if not text:
        raise UnsupportedInstruction("指令为空")
    if not any(word in text for word in SUPPORTED_ACTION_WORDS):
        raise UnsupportedInstruction("目前只支持家庭物品整理与搬运指令")

    objects = _mentioned(text, OBJECT_ALIASES)
    if not objects and any(word in text for word in ("整理", "收拾")):
        objects = ["cup", "medicine_box", "toy"]
    if not objects:
        supported = "、".join(words[0] for words in OBJECT_ALIASES.values())
        raise UnsupportedInstruction(f"没有识别到可操作物体；当前支持：{supported}")

    requested_targets: Dict[str, str] = {}
    clauses = [part for part in re.split(r"[，,；;。]|并且|然后|同时", text) if part]
    for clause in clauses:
        clause_objects = _mentioned(clause, OBJECT_ALIASES)
        target = _clause_target(clause)
        if target:
            for object_id in clause_objects:
                requested_targets[object_id] = target

    global_zones = _mentioned(text, ZONE_ALIASES)
    if len(objects) == 1 and global_zones:
        requested_targets.setdefault(objects[0], global_zones[-1])

    keep_upright = any(
        phrase in text for phrase in ("保持水杯直立", "杯子直立", "不要洒", "保持直立")
    )
    items: List[GoalItem] = []
    for object_id in objects:
        target = requested_targets.get(object_id, DEFAULT_TARGETS[object_id])
        constraints = {}
        if object_id == "cup" and keep_upright:
            constraints["upright"] = True
        items.append(GoalItem(object_id, target, constraints))

    return GoalSpec(
        instruction=instruction.strip(),
        items=items,
        goal_id=uuid.uuid4().hex[:12],
        constraints={"domain": "household_organization"},
    )


def supported_examples() -> Iterable[str]:
    return (
        "把客厅桌上的水杯和药盒送到照护区，把玩具放进收纳箱，并保持水杯直立",
        "收拾一下客厅：药品放照护台，玩具收到玩具箱",
        "把杯子送到床头，不要洒出来",
    )

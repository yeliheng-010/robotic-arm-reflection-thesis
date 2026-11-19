from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .language import parse_instruction
from .memory import MemoryStore
from .models import GoalItem, GoalSpec, PlanStep, SkillResult, WorldSnapshot
from .registry import CapabilityRegistry


@dataclass(frozen=True)
class RepairDecision:
    signature: str
    explanation: str
    strategy: Dict[str, object]


class FutureAIEmulator:
    """Deterministic stand-in for the ideal cognitive service in the concept.

    It never emits free-form motor commands.  It produces typed skill requests,
    checks capabilities, and can explain every repair decision.
    """

    def __init__(self, registry: CapabilityRegistry, memory: MemoryStore) -> None:
        self.registry = registry
        self.memory = memory

    def understand(self, instruction: str) -> GoalSpec:
        return parse_instruction(instruction)

    def plan(
        self,
        goal: GoalSpec,
        world: WorldSnapshot,
        *,
        completed: Sequence[str] = (),
        revision: int = 0,
    ) -> List[PlanStep]:
        self.registry.require(("navigate", "dock", "grasp", "place", "verify"))
        completed_set = set(completed)
        steps: List[PlanStep] = []

        def add(skill: str, target: Optional[str], explanation: str, **params: object) -> None:
            steps.append(
                PlanStep(
                    step_id=f"r{revision}-{len(steps) + 1}",
                    skill=skill,
                    target=target,
                    params=dict(params),
                    expected_world_version=world.version,
                    explanation=explanation,
                )
            )

        # A one-gripper body cannot clear a newly occupied destination while
        # carrying the user's object.  Stage the held item first, then let the
        # next planning revision clear the target and resume the original goal.
        occupied = set(world.occupied_targets)
        if world.robot.holding:
            held_item = next(
                (item for item in goal.items if item.object_id == world.robot.holding),
                None,
            )
            if held_item and held_item.target_zone in occupied:
                add(
                    "navigate",
                    "buffer_tray",
                    f"{held_item.target_zone} 突然被占用，先安全暂存 {held_item.object_id}",
                    carrying=held_item.object_id,
                )
                add("dock", "buffer_tray", "在缓冲托盘旁建立临时停靠位")
                add(
                    "place",
                    "buffer_tray",
                    f"暂存 {held_item.object_id}，释放夹爪用于清障",
                    object_id=held_item.object_id,
                    constraints=dict(held_item.constraints),
                )
                add(
                    "verify",
                    held_item.object_id,
                    f"确认 {held_item.object_id} 已安全暂存",
                    target_zone="buffer_tray",
                    constraints=dict(held_item.constraints),
                )
                return steps

        # If an injected object occupies a target, explicitly move it to the
        # buffer before working on the user's requested items.
        for entity in world.entities.values():
            target = entity.attributes.get("occupies_target")
            if target not in occupied or entity.entity_id in completed_set:
                continue
            source = entity.zone or str(target)
            add("navigate", source, f"前往 {source} 清理被占用的目标区域")
            add("dock", source, f"在 {source} 旁安全停靠")
            add("grasp", entity.entity_id, f"移走占用目标位置的 {entity.entity_id}")
            add("navigate", "buffer_tray", "把临时障碍转移到缓冲托盘")
            add("dock", "buffer_tray", "在缓冲托盘旁停靠")
            add("place", "buffer_tray", "释放临时障碍并恢复目标可用性")
            add("verify", entity.entity_id, "确认目标区域已经腾空", target_zone="buffer_tray")

        for item in self._ordered_items(goal.items, world):
            if item.object_id in completed_set:
                continue
            entity = world.entities.get(item.object_id)
            if entity is None:
                continue
            if entity.zone == item.target_zone and world.robot.holding != item.object_id:
                add(
                    "verify",
                    item.object_id,
                    f"确认已位于目标区的 {item.object_id} 状态",
                    target_zone=item.target_zone,
                    constraints=dict(item.constraints),
                )
                continue

            grasp_signature = f"grasp_lost:{item.object_id}"
            secure_memory = self.memory.find(grasp_signature, limit=1)
            grasp_profile = "secure" if secure_memory else "normal"
            source_zone = entity.zone or "living_table"
            source_target = (
                source_zone
                if source_zone in ("living_table", "care_station", "storage_bin", "buffer_tray")
                else f"object:{item.object_id}"
            )

            if world.robot.holding != item.object_id:
                add(
                    "navigate",
                    source_target,
                    f"移动到 {item.object_id} 所在的 {source_zone}",
                    object_position=list(entity.position),
                )
                add(
                    "dock",
                    source_target,
                    f"为抓取 {item.object_id} 建立稳定停靠位",
                    object_position=list(entity.position),
                )
                memory_note = "；已调用历史防滑经验" if secure_memory else ""
                add(
                    "grasp",
                    item.object_id,
                    f"抓取 {item.object_id}{memory_note}",
                    profile=grasp_profile,
                    constraints=dict(item.constraints),
                )
            route_memory = self.memory.find(f"path_blocked:{item.target_zone}", limit=1)
            avoid_corridors: List[str] = []
            if route_memory:
                avoid_corridors = list(
                    route_memory[0].context.get("blocked_corridors") or ["corridor_high"]
                )
            route_note = "；已根据历史阻塞经验调整路线" if avoid_corridors else ""
            add(
                "navigate",
                item.target_zone,
                f"携带 {item.object_id} 前往 {item.target_zone}{route_note}",
                carrying=item.object_id,
                avoid_corridors=avoid_corridors,
            )
            add("dock", item.target_zone, f"在 {item.target_zone} 旁停靠")
            add(
                "place",
                item.target_zone,
                f"将 {item.object_id} 放入 {item.target_zone}",
                object_id=item.object_id,
                constraints=dict(item.constraints),
            )
            add(
                "verify",
                item.object_id,
                f"确认 {item.object_id} 的最终位置与姿态",
                target_zone=item.target_zone,
                constraints=dict(item.constraints),
            )
        return steps

    def repair(self, result: SkillResult, target: Optional[str]) -> RepairDecision:
        code = result.failure_code or "unexpected_state"
        if code == "path_blocked":
            return RepairDecision(
                f"path_blocked:{target or 'unknown'}",
                "检测到原路径出现新障碍；停止底盘、刷新占用地图并搜索替代路线。",
                {"refresh_world": True, "avoid_new_obstacle": True},
            )
        if code in ("object_moved", "object_missing"):
            return RepairDecision(
                f"object_moved:{target or 'unknown'}",
                "目标物体位置与计划前提不一致；重新定位物体并重新选择停靠位。",
                {"refresh_world": True, "relocate_target": True},
            )
        if code == "grasp_lost":
            return RepairDecision(
                f"grasp_lost:{target or 'unknown'}",
                "夹持状态在运输中消失；回到安全姿态，重新抓取并采用更稳健的抓取配置。",
                {"refresh_world": True, "grasp_profile": "secure"},
            )
        if code == "target_occupied":
            return RepairDecision(
                f"target_occupied:{target or 'unknown'}",
                "目标区域已被占用；先将占用物移至缓冲区，再恢复原任务。",
                {"refresh_world": True, "clear_target_first": True},
            )
        return RepairDecision(
            f"unexpected_state:{target or 'unknown'}",
            "执行结果与预期不一致；保持安全状态并基于最新世界重新规划。",
            {"refresh_world": True},
        )

    @staticmethod
    def _ordered_items(
        items: Sequence[GoalItem], world: WorldSnapshot
    ) -> List[GoalItem]:
        # Finish a currently held object first.  Otherwise keep the user's
        # order, which makes explanations and demonstrations deterministic.
        holding = world.robot.holding
        return sorted(items, key=lambda item: 0 if item.object_id == holding else 1)

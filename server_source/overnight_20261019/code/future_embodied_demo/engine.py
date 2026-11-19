from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from .cognitive import FutureAIEmulator
from .language import UnsupportedInstruction, supported_examples
from .memory import MemoryStore
from .models import GoalSpec, MemoryEpisode, PlanStep, SkillResult
from .registry import CapabilityRegistry, default_mobile_manipulator_registry
from .simulator import MobileHomeSimulator
from .world import WorldModel


class DemoEngine:
    """Closed-loop observe/plan/act/verify/remember orchestration."""

    def __init__(
        self,
        *,
        simulator: Optional[MobileHomeSimulator] = None,
        memory_path: str | Path = "logs/future_ai_memory.sqlite3",
        registry: Optional[CapabilityRegistry] = None,
    ) -> None:
        self.simulator = simulator or MobileHomeSimulator()
        self.memory = MemoryStore(memory_path)
        self.registry = registry or default_mobile_manipulator_registry()
        self.cognitive = FutureAIEmulator(self.registry, self.memory)
        self.world = WorldModel()
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._replan_requested: Optional[str] = None
        self.status = "idle"
        self.goal: Optional[GoalSpec] = None
        self.plan: List[PlanStep] = []
        self.current_step: Optional[PlanStep] = None
        self.completed: List[str] = []
        self.revision = 0
        self.repair_counts: Dict[str, int] = {}
        self.logs: List[Dict[str, object]] = []
        self.last_error: Optional[str] = None
        self.world.update(self.simulator.observe())
        self._log("system", "Future AI Emulator 已就绪；未连接任何大模型 API。")

    def start(self, instruction: str, *, background: bool = True) -> Dict[str, object]:
        with self._lock:
            if self.status == "running":
                raise RuntimeError("已有任务正在执行")
            goal = self.cognitive.understand(instruction)
            self.goal = goal
            self.status = "running"
            self.plan = []
            self.current_step = None
            self.completed = []
            self.revision = 0
            self.repair_counts = {}
            self.last_error = None
            self._stop_requested = False
            self._replan_requested = None
            snapshot = self.simulator.observe()
            self.world.update(snapshot)
            self.plan = self.cognitive.plan(goal, snapshot, revision=self.revision)
            self._log(
                "goal",
                "已将受控自然语言转换为结构化家庭目标。",
                goal=goal.to_dict(),
            )
            self._log("plan", f"生成 {len(self.plan)} 个可验证技能步骤。")

        if background:
            self._thread = threading.Thread(
                target=self._run_loop, name="future-ai-demo", daemon=True
            )
            self._thread.start()
        else:
            self._run_loop()
        return goal.to_dict()

    def stop(self) -> None:
        with self._lock:
            self._stop_requested = True
            self._log("safety", "收到停止请求，将在当前技能边界进入安全状态。")

    def reset(self, *, in_place: bool = False) -> Dict[str, object]:
        self.stop()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=10.0)
        snapshot = self.simulator.soft_reset() if in_place else self.simulator.reset()
        with self._lock:
            self.status = "idle"
            self.goal = None
            self.plan = []
            self.current_step = None
            self.completed = []
            self.revision = 0
            self.repair_counts = {}
            self.last_error = None
            self._stop_requested = False
            self._replan_requested = None
            self.world.update(snapshot)
            self._log("system", "仿真场景已重置，长期记忆保留。")
        return snapshot.to_dict()

    def inject_event(self, event_type: str, target: Optional[str] = None) -> Dict[str, object]:
        result = self.simulator.inject_event(event_type, target=target)
        snapshot = self.simulator.observe()
        changes = self.world.update(snapshot)
        with self._lock:
            self._log(
                "event",
                str(result["message"]),
                event=result,
                changes=[change.__dict__ for change in changes],
            )
            if self.status == "running":
                self._replan_requested = str(result["message"])
        return result

    def state(self) -> Dict[str, object]:
        snapshot = self.simulator.observe()
        with self._lock:
            return {
                "backend": {
                    "name": "Future AI Emulator",
                    "mode": "offline_deterministic",
                    "external_api": False,
                    "assumptions": ["perfect_world_state", "instant_typed_planning", "persistent_memory"],
                },
                "status": self.status,
                "goal": self.goal.to_dict() if self.goal else None,
                "plan": [step.to_dict() for step in self.plan],
                "current_step": self.current_step.to_dict() if self.current_step else None,
                "completed": list(self.completed),
                "revision": self.revision,
                "world": snapshot.to_dict(),
                "memory": [episode.to_dict() for episode in self.memory.recent(8)],
                "capabilities": self.registry.describe(),
                "logs": list(self.logs[-80:]),
                "last_error": self.last_error,
                "examples": list(supported_examples()),
            }

    def wait(self, timeout: Optional[float] = None) -> str:
        thread = self._thread
        if thread:
            thread.join(timeout=timeout)
        return self.status

    def close(self) -> None:
        self.stop()
        self.wait(timeout=3.0)
        self.simulator.close()
        self.memory.close()

    def _run_loop(self) -> None:
        assert self.goal is not None
        while True:
            with self._lock:
                if self._stop_requested:
                    self.simulator.execute(
                        self._make_recover_step().to_request()
                    )
                    self.status = "stopped"
                    self.current_step = None
                    self._log("safety", "任务已停止，机械臂处于安全姿态。")
                    return

                if self._replan_requested:
                    reason = self._replan_requested
                    self._replan_requested = None
                    self._replan(reason)

                if self._goal_complete():
                    self.status = "completed"
                    self.current_step = None
                    self.plan = []
                    self._log("success", "所有家庭目标均已由真实世界状态验证。")
                    return

                if not self.plan:
                    self._replan("当前计划已耗尽但目标尚未完成")
                    if not self.plan:
                        self.status = "failed"
                        self.last_error = "无法为剩余目标生成可执行计划"
                        self._log("error", self.last_error)
                        return

                step = self.plan[0]
                step.status = "running"
                self.current_step = step
                self._log("action", step.explanation, step=step.to_dict())

            result = self.simulator.execute(step.to_request())
            snapshot = self.simulator.observe()
            self.world.update(snapshot)

            carrying = step.params.get("carrying")
            if result.success and carrying and snapshot.robot.holding != carrying:
                result = SkillResult(
                    step.skill,
                    False,
                    f"运输结束时未检测到 {carrying}",
                    "grasp_lost",
                    {"expected_holding": carrying, "actual_holding": snapshot.robot.holding},
                    result.metrics,
                )

            with self._lock:
                if result.success:
                    step.status = "completed"
                    self.plan.pop(0)
                    self._log("result", result.message, result=result.to_dict())
                    if step.skill == "verify" and step.target:
                        if self._verification_completes_goal(step) and step.target not in self.completed:
                            self.completed.append(step.target)
                else:
                    step.status = "failed"
                    self._handle_failure(step, result)
                    if self.status == "failed":
                        self.current_step = None
                        return

    def _handle_failure(self, step: PlanStep, result: SkillResult) -> None:
        self._log("failure", result.message, result=result.to_dict())
        repair_target = result.observed_effects.get("expected_holding") or step.target
        decision = self.cognitive.repair(result, str(repair_target) if repair_target else None)
        count = self.repair_counts.get(decision.signature, 0) + 1
        self.repair_counts[decision.signature] = count
        self.memory.record(
            MemoryEpisode(
                signature=decision.signature,
                context={
                    "world_version": self.simulator.observe().version,
                    "blocked_corridors": list(self.simulator.observe().blocked_corridors),
                    "step": step.to_dict(),
                    "result": result.to_dict(),
                },
                repair=decision.strategy,
                outcome="repair_planned",
                task_id=self.goal.goal_id if self.goal else None,
            )
        )
        self._log(
            "repair",
            decision.explanation,
            signature=decision.signature,
            strategy=decision.strategy,
            attempt=count,
        )
        if count > 3:
            self.status = "failed"
            self.last_error = f"同类异常连续修正失败：{decision.signature}"
            self.plan = []
            self._log("error", self.last_error)
            return
        self._replan_requested = None
        self.simulator.execute(self._make_recover_step().to_request())
        self._replan(decision.explanation)

    def _replan(self, reason: str) -> None:
        if self.goal is None:
            return
        snapshot = self.simulator.observe()
        self.world.update(snapshot)
        self.revision += 1
        self.plan = self.cognitive.plan(
            self.goal,
            snapshot,
            completed=self.completed,
            revision=self.revision,
        )
        self.current_step = None
        self._log(
            "replan",
            f"因“{reason}”生成修订计划 r{self.revision}，共 {len(self.plan)} 步。",
        )

    def _goal_complete(self) -> bool:
        if self.goal is None:
            return False
        snapshot = self.simulator.observe()
        for item in self.goal.items:
            if item.object_id not in self.completed:
                return False
            entity = snapshot.entities.get(item.object_id)
            if entity is None or entity.zone != item.target_zone:
                return False
            if item.constraints.get("upright") and not entity.attributes.get("upright"):
                return False
        return snapshot.robot.holding is None

    def _verification_completes_goal(self, step: PlanStep) -> bool:
        if step.target == "target_blocker":
            return True
        if self.goal is None:
            return False
        expected = next(
            (item.target_zone for item in self.goal.items if item.object_id == step.target),
            None,
        )
        return expected is not None and step.params.get("target_zone") == expected

    @staticmethod
    def _make_recover_step() -> PlanStep:
        return PlanStep("safety-recover", "recover", explanation="恢复安全姿态")

    def _log(self, kind: str, message: str, **details: object) -> None:
        self.logs.append(
            {
                "timestamp": time.time(),
                "kind": kind,
                "message": message,
                "details": details,
            }
        )
        if len(self.logs) > 500:
            del self.logs[:-500]


__all__ = ["DemoEngine", "UnsupportedInstruction"]

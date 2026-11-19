from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from .models import CapabilitySpec


@dataclass
class EmbodiedAgent:
    agent_id: str
    description: str
    capabilities: Dict[str, CapabilitySpec] = field(default_factory=dict)

    def add_capability(self, capability: CapabilitySpec) -> None:
        if capability.provider != self.agent_id:
            raise ValueError(
                f"capability provider {capability.provider!r} does not match {self.agent_id!r}"
            )
        self.capabilities[capability.name] = capability


class CapabilityRegistry:
    """Runtime catalogue of bodies and the skills they expose."""

    def __init__(self) -> None:
        self._agents: Dict[str, EmbodiedAgent] = {}

    def register(self, agent: EmbodiedAgent) -> None:
        if agent.agent_id in self._agents:
            raise ValueError(f"agent already registered: {agent.agent_id}")
        self._agents[agent.agent_id] = agent

    def providers_for(self, capability_name: str) -> List[EmbodiedAgent]:
        return [
            agent
            for agent in self._agents.values()
            if capability_name in agent.capabilities
        ]

    def require(self, names: Iterable[str]) -> None:
        missing = [name for name in names if not self.providers_for(name)]
        if missing:
            raise RuntimeError(f"no embodied provider for: {', '.join(missing)}")

    def describe(self) -> Dict[str, object]:
        return {
            agent_id: {
                "description": agent.description,
                "capabilities": sorted(agent.capabilities),
            }
            for agent_id, agent in self._agents.items()
        }


def default_mobile_manipulator_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    base = EmbodiedAgent("mobile_base", "三自由度家庭移动底盘")
    base.add_capability(
        CapabilitySpec(
            "navigate",
            "mobile_base",
            "在占用地图中移动到目标功能区",
            ("target_zone",),
            ("arm_parked",),
            ("stop_on_collision", "no_motion_with_extended_arm"),
        )
    )
    base.add_capability(
        CapabilitySpec(
            "dock",
            "mobile_base",
            "在家具旁精确停靠",
            ("target_zone",),
            ("arm_parked",),
            ("stop_on_collision",),
        )
    )
    registry.register(base)

    arm = EmbodiedAgent("ur5e_arm", "安装在移动底盘上的 UR5e 与二指夹爪")
    for name, description, inputs, preconditions in (
        ("grasp", "抓取可达物体", ("object_id",), ("docked", "empty_gripper")),
        ("place", "将所持物体放入目标区域", ("target_zone",), ("docked", "holding_object")),
        ("recover", "收拢机械臂并恢复安全状态", (), (),),
        ("verify", "验证动作后的物理世界状态", ("predicate",), (),),
    ):
        arm.add_capability(
            CapabilitySpec(
                name,
                "ur5e_arm",
                description,
                inputs,
                preconditions,
                ("joint_limits", "workspace_check", "collision_stop"),
            )
        )
    registry.register(arm)

    observer = EmbodiedAgent("sim_oracle", "代表零幻觉假设的 MuJoCo 状态观察器")
    observer.add_capability(
        CapabilitySpec("observe", "sim_oracle", "生成无遗漏世界快照")
    )
    registry.register(observer)
    return registry

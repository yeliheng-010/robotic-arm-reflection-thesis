"""错误分类体系与结构化错误报告。

论文中的错误按任务流水线的四个阶段组织：

    规划/语义 (PLANNING)  →  感知/定位 (PERCEPTION)  →  抓取执行 (EXECUTION)  →  放置结果 (PLACEMENT)

每个检测器只输出 `ErrorReport`，不直接决定如何修正；修正由反思模块完成。
这样"错误反馈"与"智能反思"两部分在代码和论文结构上都是解耦的。
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Stage(str, Enum):
    PLANNING = "planning"
    PERCEPTION = "perception"
    EXECUTION = "execution"
    PLACEMENT = "placement"


class ErrorType(str, Enum):
    # 规划/语义错误
    PLAN_PARSE_ERROR = "plan_parse_error"            # 规划输出不是合法 JSON
    PLAN_SEQUENCE_INVALID = "plan_sequence_invalid"  # 动作时序违反约束
    PLAN_TARGET_MISSING = "plan_target_missing"      # 规划没有包含被操作物体或放置目标
    PLAN_WRONG_OBJECT = "plan_wrong_object"          # 规划选择的物体与指令语义不符

    # 感知/定位错误
    GROUNDING_OFF_TARGET = "grounding_off_target"    # 定位点没有落在目标物体上
    GROUNDING_OUT_OF_IMAGE = "grounding_out_of_image"
    DEPTH_INVALID = "depth_invalid"
    MASK_INVALID = "mask_invalid"                    # 分割掩码为空/过小/过大
    NO_GRASP_CANDIDATE = "no_grasp_candidate"

    # 抓取执行错误
    IK_FAILURE = "ik_failure"
    EMPTY_GRASP = "empty_grasp"                      # 夹爪闭合后没有夹住物体
    WRONG_OBJECT_GRASPED = "wrong_object_grasped"
    OBJECT_DROPPED = "object_dropped"                # 搬运途中物体脱落
    COLLISION = "collision"                          # 机械臂/夹爪与环境发生意外碰撞

    # 放置结果错误
    PLACEMENT_OFFSET = "placement_offset"            # 放置位置偏离目标
    OBJECT_OUTSIDE_CONTAINER = "object_outside_container"
    OBJECT_TOPPLED = "object_toppled"
    VISUAL_VERIFICATION_FAILED = "visual_verification_failed"  # VLM 看图判定未完成


ERROR_STAGE: Dict[ErrorType, Stage] = {
    ErrorType.PLAN_PARSE_ERROR: Stage.PLANNING,
    ErrorType.PLAN_SEQUENCE_INVALID: Stage.PLANNING,
    ErrorType.PLAN_TARGET_MISSING: Stage.PLANNING,
    ErrorType.PLAN_WRONG_OBJECT: Stage.PLANNING,
    ErrorType.GROUNDING_OFF_TARGET: Stage.PERCEPTION,
    ErrorType.GROUNDING_OUT_OF_IMAGE: Stage.PERCEPTION,
    ErrorType.DEPTH_INVALID: Stage.PERCEPTION,
    ErrorType.MASK_INVALID: Stage.PERCEPTION,
    ErrorType.NO_GRASP_CANDIDATE: Stage.PERCEPTION,
    ErrorType.IK_FAILURE: Stage.EXECUTION,
    ErrorType.EMPTY_GRASP: Stage.EXECUTION,
    ErrorType.WRONG_OBJECT_GRASPED: Stage.EXECUTION,
    ErrorType.OBJECT_DROPPED: Stage.EXECUTION,
    ErrorType.COLLISION: Stage.EXECUTION,
    ErrorType.PLACEMENT_OFFSET: Stage.PLACEMENT,
    ErrorType.OBJECT_OUTSIDE_CONTAINER: Stage.PLACEMENT,
    ErrorType.OBJECT_TOPPLED: Stage.PLACEMENT,
    ErrorType.VISUAL_VERIFICATION_FAILED: Stage.PLACEMENT,
}

# 面向用户/论文展示的中文说明
ERROR_DESCRIPTION_ZH: Dict[ErrorType, str] = {
    ErrorType.PLAN_PARSE_ERROR: "规划输出无法解析为合法 JSON",
    ErrorType.PLAN_SEQUENCE_INVALID: "动作序列违反时序约束",
    ErrorType.PLAN_TARGET_MISSING: "规划缺少被操作物体或放置目标",
    ErrorType.PLAN_WRONG_OBJECT: "规划选择的物体与指令不符",
    ErrorType.GROUNDING_OFF_TARGET: "视觉定位点没有落在目标物体上",
    ErrorType.GROUNDING_OUT_OF_IMAGE: "视觉定位点超出图像范围",
    ErrorType.DEPTH_INVALID: "定位点深度无效",
    ErrorType.MASK_INVALID: "目标分割掩码异常",
    ErrorType.NO_GRASP_CANDIDATE: "没有可行的抓取候选",
    ErrorType.IK_FAILURE: "逆运动学无解，目标位姿不可达",
    ErrorType.EMPTY_GRASP: "夹爪闭合后未夹住物体（空抓）",
    ErrorType.WRONG_OBJECT_GRASPED: "夹住了错误的物体",
    ErrorType.OBJECT_DROPPED: "搬运过程中物体脱落",
    ErrorType.COLLISION: "机械臂与环境发生意外碰撞",
    ErrorType.PLACEMENT_OFFSET: "放置位置偏离目标",
    ErrorType.OBJECT_OUTSIDE_CONTAINER: "物体落在容器外",
    ErrorType.OBJECT_TOPPLED: "物体放置后倾倒",
    ErrorType.VISUAL_VERIFICATION_FAILED: "视觉验证判定任务未完成",
}


@dataclass
class ErrorReport:
    """一次检测到的错误。evidence 中只放可序列化的数值/字符串，供反思模块与记忆库使用。"""

    error_type: ErrorType
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    action_index: Optional[int] = None
    detector: str = ""
    # 可选：发生错误时的图像路径（反思时一并交给 VLM）
    image_paths: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def stage(self) -> Stage:
        return ERROR_STAGE[self.error_type]

    def describe_zh(self) -> str:
        return f"[{self.stage.value}] {ERROR_DESCRIPTION_ZH[self.error_type]}：{self.message}"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["error_type"] = self.error_type.value
        data["stage"] = self.stage.value
        return data


class TaskAbort(Exception):
    """执行过程中检测到错误、需要中止本次尝试并交给反思模块。"""

    def __init__(self, report: ErrorReport):
        super().__init__(report.describe_zh())
        self.report = report

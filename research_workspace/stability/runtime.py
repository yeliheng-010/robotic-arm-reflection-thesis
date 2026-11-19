"""完整场景固定网格与上一轮候选生成器的独立实验引擎。"""
from unittest.mock import patch
from contextlib import ExitStack
import grasp_process as grasp
import geometry.runtime as previous_runtime
from geometry.runtime import GeometryEngine
from stability.detector import StableDetector
from stability.proposals import generate
from stability.inference import infer
from stability.monitor import guard_environment
from stability.prepose import approach_context
from stability.kinematics import set_robot_config
from manipulator_grasp.arm.robot import UR5e


class StableEngine(GeometryEngine):
    def __init__(self, *, stable=True, **kwargs):
        super().__init__(arm='multi', **kwargs)
        self.stable = stable

    def _attempt(self, *args, **kwargs):
        trace = {}
        detector = StableDetector if self.stable else grasp.ModelFreeCollisionDetector
        with ExitStack() as stack:
            stack.enter_context(patch.object(grasp, 'ModelFreeCollisionDetector', detector))
            if self.stable:
                stack.enter_context(patch.object(UR5e, 'set_robot_config', set_robot_config))
                stack.enter_context(approach_context(trace, ignore=(args[0], args[1])))
                stack.enter_context(guard_environment())
                stack.enter_context(patch.object(previous_runtime, 'generate', generate))
                stack.enter_context(patch.object(grasp, 'run_grasp_inference', infer))
            record, report = super()._attempt(*args, **kwargs)
        record['stable_voxel_grid'] = self.stable
        record['approach_plan'] = trace
        return record, report

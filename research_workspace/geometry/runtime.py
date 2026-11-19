"""进程内临时替换几何生成器，并保留初始状态与最终候选。"""
from contextlib import ExitStack, contextmanager
from unittest.mock import patch
import grasp_process as grasp
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from training.refine.engine import EvidenceEngine
from geometry.candidates import generate


@contextmanager
def capture_candidates(arm, trace):
    original_inference = grasp.run_grasp_inference
    original_render = UR5GraspEnv.render
    generator = generate if arm == 'multi' else grasp.generate_geometric_topdown_grasp

    def traced_generate(points):
        group = generator(points)
        trace['generated'] = group.grasp_group_array.tolist()
        return group

    def inference(*args, **kwargs):
        group = original_inference(*args, **kwargs)
        trace['returned'] = group.grasp_group_array.tolist()
        return group

    def render(env, *args, **kwargs):
        if 'initial_qpos' not in trace:
            trace['initial_qpos'] = env.mj_data.qpos.tolist()
            trace['initial_body_xyz'] = env.mj_data.xpos.tolist()
        return original_render(env, *args, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.object(grasp, 'generate_geometric_topdown_grasp', traced_generate))
        stack.enter_context(patch.object(grasp, 'run_grasp_inference', inference))
        stack.enter_context(patch.object(UR5GraspEnv, 'render', render))
        yield


class GeometryEngine(EvidenceEngine):
    def __init__(self, *, arm, **kwargs):
        super().__init__(**kwargs)
        self.arm = arm

    def _attempt(self, *args, **kwargs):
        trace = {'arm': self.arm, 'source': 'geometric_candidates_with_rule_reflection'}
        with capture_candidates(self.arm, trace):
            record, report = super()._attempt(*args, **kwargs)
        record['candidate_trace'] = trace
        return record, report

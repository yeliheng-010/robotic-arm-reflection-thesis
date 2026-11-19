"""适配现有同观测候选阶段；真实 MuJoCo 验证待单独登记。"""
import hashlib
import json
import numpy as np
from observed_top_pose_v1.top_fit import estimate
from model_grasp_intent_v1.contract import require
from model_grasp_intent_v1.geometry import propose


class PlannerBridge:
    def __init__(self, points, plan, *, stage, pose_factory):
        self.points = np.asarray(points, dtype=float).copy()
        self.fitted = estimate(self.points)
        self.plan, self.stage, self.pose_factory = plan, stage, pose_factory
        self.private_result = None

    def __call__(self, proposal):
        require(proposal.get('status') == 'proposal', 'invalid_proposal')
        action = proposal['action']
        name = hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest()[:16]
        def generator(nominal, fitted):
            require(fitted == self.fitted, 'observation_mismatch')
            rebuilt = propose(self.points, nominal.t, action)
            require(rebuilt['status'] == 'proposal', 'proposal_revalidation_failed')
            require(np.array_equal(rebuilt['pose'], proposal['pose']), 'proposal_mismatch')
            return [dict(id='model_intent_'+name, pose=self.pose_factory(np.array(rebuilt['pose'])))]
        self.private_result = self.stage(generator, self.plan)
        require(type(self.private_result) is dict and 'selected' in self.private_result,
                'invalid_stage_result')
        return dict(status='ready' if self.private_result['selected'] is not None else 'rejected')


def runtime_bridge(points, plan):
    """调用方必须已进入 jv_context.observation 和原始安全上下文。"""
    import spatialmath as sm
    from jv_context import stage
    return PlannerBridge(points, plan, stage=stage, pose_factory=sm.SE3)

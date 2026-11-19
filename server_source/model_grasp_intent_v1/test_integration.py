"""真契约/几何/控制器/适配器联合测试；模型和物理规划是显式替身。"""
import json
from types import SimpleNamespace
import unittest
import numpy as np
from observed_top_pose_v1.top_fit import estimate
from model_grasp_intent_v1.model import ModelPolicy
from model_grasp_intent_v1.bridge import PlannerBridge
from model_grasp_intent_v1.loop import run
from model_grasp_intent_v1.test_adapters import FakeGenerator
from model_grasp_intent_v1.test_contract import intent
from model_grasp_intent_v1.test_geometry import points
from model_grasp_intent_v1.test_loop import observation, limits


class FeedbackGenerator(FakeGenerator):
    """手工编写的测试替身，不是模型自主决策结果。"""
    def generate(self, messages):
        request = json.loads(messages[1]['content'])
        action = intent(depth_mm=15 if request['history'] else 30)
        return dict(finish_reason='stop', text=json.dumps(dict(action=action)))


class IntegrationTests(unittest.TestCase):
    def test_model_contract_to_geometry_to_rejection_to_new_proposal(self):
        poses = []
        def stage(generator, plan):
            row = generator(SimpleNamespace(t=np.array([.8, .4, .76])), estimate(points()))[0]
            poses.append(row['pose'])
            return plan()
        def plan():
            return dict(selected={'fixture': True} if len(poses) == 2 else None,
                        private_truth='PRIVATE_VALUE')
        generator = FeedbackGenerator()
        policy = ModelPolicy(generator, max_calls=4)
        bridge = PlannerBridge(points(), plan, stage=stage, pose_factory=lambda value: value)
        result = run(observation(), policy, bridge, budget=limits())
        self.assertEqual('plan_ready_unverified', result['status'])
        self.assertEqual(2, policy.generations)
        self.assertAlmostEqual(.015, poses[1][2, 3]-poses[0][2, 3])
        self.assertNotIn('PRIVATE_VALUE', str(generator.seen))
        self.assertNotIn('PRIVATE_VALUE', str(result))
        self.assertIsNone(result['task_success'])
        self.assertEqual(0, result['physical_attempts'])

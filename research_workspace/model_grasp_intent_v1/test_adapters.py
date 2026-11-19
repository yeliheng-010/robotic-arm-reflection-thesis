import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from observed_top_pose_v1.top_fit import estimate
from model_grasp_intent_v1.model import ModelPolicy
from model_grasp_intent_v1.bridge import PlannerBridge
from model_grasp_intent_v1.geometry import propose
from model_grasp_intent_v1.requests import build
from model_grasp_intent_v1.test_contract import intent
from model_grasp_intent_v1.test_geometry import points
from model_grasp_intent_v1.test_loop import observation, limits


class FakeGenerator:
    """只验证已有生成器协议，不代表实际模型调用。"""
    def __init__(self):
        self.finish = 'stop'
        self.text = json.dumps(dict(action=intent(tilt_deg=60)))
        self.seen = []

    def prepare(self, messages):
        self.seen.append(messages)
        return messages

    def prepare_images(self, messages, paths):
        self.seen.append(paths)
        return messages, {'test_double': True}

    def generate(self, values):
        return dict(finish_reason=self.finish, text=self.text)


def request():
    return build(observation(), limits(), history=[], can_observe=False)


class AdapterTests(unittest.TestCase):
    def test_generated_direction_is_preserved_and_budget_enforced(self):
        generator = FakeGenerator()
        policy = ModelPolicy(generator, max_calls=1)
        self.assertEqual(intent(tilt_deg=60), policy(request())['action'])
        self.assertEqual(1, policy.calls)
        with self.assertRaises(ValueError):
            policy(request())
        self.assertEqual(1, len(generator.seen))

    def test_non_eos_and_duplicate_keys_rejected(self):
        for finish, text in [('length', '{"action":{"id":"STOP","args":{}}}'),
                             ('stop', '{"action":{},"action":{"id":"STOP","args":{}}}')]:
            generator = FakeGenerator()
            generator.finish, generator.text = finish, text
            with self.subTest(finish=finish), self.assertRaises(ValueError):
                ModelPolicy(generator, max_calls=1)(request())

    def test_images_cannot_be_reused_for_a_new_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'view.png'
            path.write_bytes(b'test-only-file-not-a-real-image')
            row = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            generator = FakeGenerator()
            policy = ModelPolicy(generator, max_calls=2, images={0: [row]}, image_root=directory)
            policy(request())
            changed = request()
            changed['observation']['revision'] = 1
            with self.assertRaises(ValueError):
                policy(changed)
            self.assertEqual(1, len(generator.seen))

    def test_tampered_image_rejected_before_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'view.png'
            path.write_bytes(b'original')
            row = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            policy = ModelPolicy(FakeGenerator(), max_calls=1, images={0: [row]}, image_root=directory)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                policy(request())

    def test_stage_receives_only_model_pose(self):
        rows = []
        def stage(generator, plan):
            rows.extend(generator(SimpleNamespace(t=np.array([.8, .4, .76])), estimate(points())))
            return plan()
        bridge = PlannerBridge(points(), lambda: dict(selected={'test_only': True}),
                               stage=stage, pose_factory=lambda matrix: matrix)
        proposal = propose(points(), [.8, .4, .76], intent(tilt_deg=60))
        self.assertEqual('ready', bridge(proposal)['status'])
        self.assertEqual(1, len(rows))
        np.testing.assert_allclose(proposal['pose'], rows[0]['pose'])

    def test_stage_rejects_mismatched_observation(self):
        def stage(generator, plan):
            return generator(SimpleNamespace(t=np.array([.8, .4, .76])), estimate(points()+[.1, 0, 0]))
        bridge = PlannerBridge(points(), lambda: self.fail('must not plan'),
                               stage=stage, pose_factory=lambda matrix: matrix)
        with self.assertRaises(ValueError):
            bridge(propose(points(), [.8, .4, .76], intent()))

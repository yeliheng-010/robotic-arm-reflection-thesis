from copy import deepcopy
import unittest
from action_space_audit_v1.cache import reused
from model_grasp_intent_v1.test_contract import intent


class CacheTests(unittest.TestCase):
    def fixture(self):
        proposal=dict(action=intent(),pose=[[1,0],[0,1]])
        saved=dict(proposal=deepcopy(proposal),endpoints=[dict(config=[1,1,1],ok=False,reason='collision')])
        return proposal,saved

    def test_identical_input_reuses_independent_copy(self):
        proposal,saved=self.fixture()
        result=reused(proposal,saved)
        self.assertEqual(saved['endpoints'],result)
        result[0]['ok']=True
        self.assertFalse(saved['endpoints'][0]['ok'])

    def test_pose_mismatch_is_not_cached(self):
        proposal,saved=self.fixture()
        proposal['pose'][0][0]=2
        with self.assertRaises(ValueError):
            reused(proposal,saved)

    def test_different_action_is_not_cached(self):
        proposal,saved=self.fixture()
        proposal['action']=intent(depth_mm=15)
        self.assertIsNone(reused(proposal,saved))

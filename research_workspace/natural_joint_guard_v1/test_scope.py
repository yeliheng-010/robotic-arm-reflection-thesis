import unittest
from types import SimpleNamespace
import numpy as np
from bounded_ik_v2 import sample_wrapper


class ScopeTests(unittest.TestCase):
    def check(self, *, continuous, target=4.):
        robot = SimpleNamespace(get_joint=lambda: np.zeros(6))
        env = SimpleNamespace(joint_names=list(range(6)))
        data = SimpleNamespace(joint=lambda n: SimpleNamespace(qpos=[target]))
        function = sample_wrapper(lambda *a,**k: dict(ok=True),np.tile([-6.,6.],(6,1)),continuous=continuous)
        return function(robot,env,data,value=None,ignore=())

    def test_independent_endpoint_not_a_trajectory_jump(self):
        self.assertTrue(self.check(continuous=False)['ok'])
        self.assertEqual('discontinuous_joint_branch',self.check(continuous=True)['reason'])

    def test_both_scopes_keep_limits(self):
        for scope in (False,True):
            self.assertEqual('joint_or_control_limit',self.check(continuous=scope,target=7.)['reason'])


if __name__=='__main__':
    unittest.main()

from contextlib import contextmanager
from unittest.mock import patch
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from route_audit_v3 import rebuild
from routecheck.static import state, unchanged
from model_grasp_gpu_v1.planning import integration, forbid
from action_space_audit_v1.common import QUALIFIED, read


@contextmanager
def opened(manifest):
    case = manifest['case']
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']),mode(case['control']), \
         patch.object(mujoco,'mj_step',forbid),patch.object(mujoco,'mj_step1',forbid), \
         patch.object(mujoco,'mj_step2',forbid):
        flow = rebuild(case,read(QUALIFIED/'actual_plan.json'))
        before,full = state(flow.robot,flow.env),integration(flow)
        try:
            yield flow
        finally:
            unchanged(before,state(flow.robot,flow.env))
            np.testing.assert_array_equal(full,integration(flow))

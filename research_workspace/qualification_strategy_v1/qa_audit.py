"""从真实规划上下文和真实点云独立重建，不重跑推理或运动。"""
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import goal_search
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from top_runtime import filter_context
from cc_audit import visibility
from qs_common import ROOT, read, save, sha, verify
from qs_probe import endpoints

RUN = ROOT/'actual'


def main(name):
    verify(RUN/'manifest.json')
    folder = RUN/'cases'/name
    saved = verify(folder/'result.json')
    case, plan = saved['case'], read(folder/'actual_plan.json')
    seen = visibility(folder/'initial_visibility.json', case['config'])
    assert seen['accepted']
    with np.load(folder/'span_inputs.npz') as arrays:
        points = arrays['world_points']
    trace = {}
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
         self_context(), joint_context(case['config']), mode(case['control']), filter_context(points, trace), \
         patch.object(goal_search, 'LIFTS', (case['state']['parameters']['lift_height'],)):
        flow = rebuild(case, plan)
        actual = goal_search.choose(flow, item=case['item'], parameters=case['state']['parameters'],
            hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
    assert actual == plan
    assert trace['observed_top_estimate'] == saved['span']['observed_top_estimate']
    assert not read(folder/'bridge.json')['planners']
    save(RUN/'audits'/(name+'.json'), dict(passed=True, qualified=saved['qualified'],
        endpoints=endpoints(plan), visibility=seen, fit=trace['observed_top_estimate'],
        nominal=saved['nominal'], independent_plan_identical=True, physical_attempts=0,
        identities={str(folder/'result.json'): sha(folder/'result.json')}))
    print(dict(id=name, passed=True, qualified=saved['qualified']), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])

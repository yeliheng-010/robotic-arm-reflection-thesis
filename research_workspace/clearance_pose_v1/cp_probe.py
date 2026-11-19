"""只在真实初态快照中扩大候选；全部原保护和预算保持。"""
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import goal_search
import top_runtime
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from qs_probe import endpoints
from cp_candidates import candidates
from cp_common import RUN, SOURCE, current, read, save, sha, verify


def inspect(row):
    source = SOURCE/'cases'/row['name']
    recorded = verify(source/'result.json')
    case, old_plan = recorded['case'], read(source/'actual_plan.json')
    with np.load(source/'span_inputs.npz') as arrays:
        points = arrays['world_points']
    trace = {}
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
         self_context(), joint_context(case['config']), mode(case['control']), \
         patch.object(top_runtime, 'candidates', candidates), top_runtime.filter_context(points, trace), \
         patch.object(goal_search, 'LIFTS', (case['state']['parameters']['lift_height'],)):
        flow = rebuild(case, old_plan)
        plan = goal_search.choose(flow, item=case['item'], parameters=case['state']['parameters'],
            hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
    assert plan['context'] == old_plan['context']
    assert trace['observed_top_estimate'] == recorded['span']['observed_top_estimate']
    return plan, trace


def main(name, mode):
    assert mode in ('probe', 'audit')
    row = current(name)
    output = RUN/mode/name
    output.mkdir(parents=True, exist_ok=False)
    plan, trace = inspect(row)
    if mode == 'audit':
        assert plan == read(RUN/'probe'/name/'plan.json')
        assert trace == read(RUN/'probe'/name/'result.json')['trace']
    save(output/'plan.json', plan)
    result = dict(id=name, passed=True, qualified=plan['selected'] is not None,
        independently_reproduced=mode == 'audit', status=plan['status'], trace=trace,
        endpoints=endpoints(plan), selected_id=(plan['selected'] or {}).get('id'),
        physical_attempts=0, model_calls=0, identities={str(output/'plan.json'): sha(output/'plan.json')})
    save(output/'result.json', result)
    print({k:result[k] for k in ('id','qualified','status','endpoints','selected_id')}, flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])

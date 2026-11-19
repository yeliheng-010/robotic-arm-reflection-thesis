"""实际观测快照静态回归；独立进程复算，不执行动作。"""
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import goal_search
from route_audit_v3 import rebuild
from audit_motion_live import UR5e,set_robot_config,guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode as control_mode
from top_runtime import filter_context
from jg_choose import choose
from jg_register import RUN,read,save,sha,verify


def inspect(entry):
    folder,case = Path(entry['folder']),entry['case']
    previous = read(entry['plan'])
    with np.load(folder/'span_inputs.npz') as arrays:
        points = arrays['world_points']
    trace,events = {},[]
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']),control_mode(case['control']), \
         filter_context(points,trace),patch.object(goal_search,'LIFTS',(case['state']['parameters']['lift_height'],)):
        flow = rebuild(case,previous)
        plan = choose(flow,item=case['item'],parameters=case['state']['parameters'],
                      hooks=(grasp.move_to_grasp_pose,grasp.move_to_point),events=events)
    assert plan['context'] == previous['context']
    assert trace['observed_top_estimate'] == read(folder/'span_guard.json')['observed_top_estimate']
    return plan,trace,events


def reference(entry, plan):
    if not entry['successful']:
        return dict(previous_success=False)
    selected = plan['selected']
    assert selected is not None, entry['name']
    previous = read(entry['plan'])['selected']
    comparable = {k:v for k,v in selected.items() if k!='joint_option'}
    assert comparable == previous, entry['name']
    return dict(previous_success=True,selected_fields_identical=True,
        equivalent_angle_used='joint_option' in selected)


def main(name, mode):
    manifest = verify(RUN/'manifest.json')
    entry = next(r for r in manifest['rows'] if r['name']==name)
    plan,trace,events = inspect(entry)
    folder = RUN/mode/name
    save(folder/'plan.json',plan)
    save(folder/'trace.json',trace)
    save(folder/'events.json',events)
    unchanged = reference(entry,plan)
    if mode == 'audit':
        assert plan == read(RUN/'probe'/name/'plan.json')
        assert events == read(RUN/'probe'/name/'events.json')
        assert trace == read(RUN/'probe'/name/'trace.json')
    save(folder/'result.json',dict(passed=True,qualified=plan['selected'] is not None,
        reference=unchanged,independent=mode=='audit',status=plan['status'],checks=len(events),
        physical_attempts=0,model_calls=0,identities={str(p):sha(p) for p in folder.glob('*.json')}))
    print(dict(name=name,mode=mode,qualified=plan['selected'] is not None,checks=len(events)),flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])

"""真实输入严格配对后复算完整路径，禁止不同现场复用冻结目标。"""
import json
import numpy as np
from pathlib import Path
from unittest.mock import patch
from cm_planning import context as saved_context
from waypoint_paths import corridor
import hp_search
import hp_carry
from hv_search import explore
from hv_geometry import inspect
from op_common import entry,STATIC,read,save,sha


def pair(folder):
    original=Path(entry()['folder'])/'span_inputs.npz'
    with np.load(original) as old,np.load(folder/'span_inputs.npz') as new:
        assert set(old.files)==set(new.files)
        for name in old.files:
            np.testing.assert_array_equal(old[name],new[name])
    return dict(passed=True,identical_arrays=old.files,source_sha256=sha(original))


def replay(flow, case, parameters):
    row=entry()
    assert saved_context(flow,parameters)==read(row['plan'])['context']
    for key in ('item','config','state','control','strategy'):
        assert case[key]==row['case'][key]
    with open(row['endpoint_path']) as stream:
        goals=[r for r in map(json.loads,stream) if r['ok']]
    with patch.object(hp_search,'explore',explore),patch.object(hp_carry,'inspect',inspect):
        plan=hp_search.choose(flow,item=case['item'],parameters=parameters,goals=goals,record=lambda *args:None)
    assert plan==read(STATIC/'audit'/row['name']/'plan.json')
    return plan


def legacy(flow, plan, parameters):
    chosen=plan['selected']
    selected=dict(chosen['prefix'],lift=chosen['lift'],target=np.array(chosen['goal']['release'])[:3,3].tolist(),
        goal=chosen['goal'],transport_route='direct',held_selection=chosen)
    edges=corridor(flow.env,entry()['case']['item']['destination'])
    return dict(context=saved_context(flow,parameters),selected=selected,oriented_plan=plan,
        endpoints=dict(passing=read(Path(entry()['endpoint_path']).with_name('result.json'))['safe_endpoints']),edges=[x.tolist() for x in edges],
        planning_family='oriented_transfer_v1',unchanged=True)


def selecting(session):
    def choose(flow, **kwargs):
        inputs=pair(session.folder)
        plan=replay(flow,session.case,kwargs['parameters'])
        save(session.folder/'oriented_plan.json',plan)
        save(session.folder/'approved_plan_match.json',dict(passed=True,inputs=inputs,
            actual_plan_identical=True,stopped_before_motion=session.planning_only))
        if session.planning_only:
            from qa_runtime import PlanningComplete
            raise PlanningComplete()
        return legacy(flow,plan,kwargs['parameters'])
    return choose

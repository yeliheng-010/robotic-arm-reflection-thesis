"""复算真实命令、当前持物检查、原观测/接触/传感/释放/归位审计。"""
from unittest.mock import patch
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import rb_audit
import sv_strategy_audit
import top_runtime
from lc_candidates import candidates
from audit_v5 import audit_attempt
from audit_motion_live import rebuild,RecordedPlanner,UR5e,set_robot_config,guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from hv_geometry import inspect
from ta_audit import observations
from rh_audit import return_audit
from sr_audit import measured
from live_motion import plan_values
from commands import build
from op_common import TRIAL,STATIC,entry,read,save,sha,verify
from op_choose import pair
from op_audit_geometry import audit as geometry


def live_check(case, folder):
    path=folder/'live_held_check.json'
    if not path.exists():
        return dict(entered=False)
    record=read(path)
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']):
        robot,env=rebuild(case,record['context'])
        segments=[(leg['phase'],RecordedPlanner(leg),leg['duration']) for leg in record['legs']]
        current=inspect(robot,env,segments,item=case['item'],grasp=sm.SE3(np.array(record['grasp'])))
    for field in ('feasible','samples','phase','time'):
        assert current[field]==record['result'][field]
    if current['failure']:
        assert current['failure']['reason']==record['result']['failure']['reason']
    return dict(entered=True,passed=True,feasible=current['feasible'],result=current)


def command_check(case, folder):
    rows=[r for r in read(folder/'bridge.json')['planners'] if r['action']=='move_to_point']
    if not rows:
        return dict(entered=False)
    assert len(rows)==1
    recorded=rows[0]
    selection=read(folder/'oriented_plan.json')['selected']
    planners,times,_=build(selection,case['state']['parameters']['time_scale'])
    segments=[('move_to_point_'+str(i),p,t) for i,(p,t) in enumerate(zip(planners,times))]
    assert recorded['legs']==plan_values(segments)
    assert recorded['durations']==[0.,*times]
    return dict(entered=True,passed=True,executed=recorded['executed'],durations=times)


def main():
    case=entry()['case']
    folder=TRIAL/'cases'/str(case['item']['seed'])/'first'
    step=read(folder/'step.json')
    result=read(folder.parent/'result.json')
    assert result['manifest_sha256']==sha(TRIAL/'manifest.json')
    assert result['physical_attempts']==step['index']==1
    assert read(folder/'approved_plan_match.json')['actual_plan_identical']
    seen=observations(case,folder)
    live=live_check(case,folder)
    commands=command_check(case,folder)
    with patch.object(top_runtime,'candidates',candidates),patch.object(rb_audit,'geometry',geometry), \
         patch.object(sv_strategy_audit,'audit_attempt',audit_attempt):
        checked=sv_strategy_audit.inspect(case,step)
    returning=return_audit(case,folder) if (folder/'return_plan.json').exists() else None
    contact=measured(folder)
    assert contact['self_contact_samples']==0
    assert step['success']==result['new_success']
    verify(TRIAL/'manifest.json')
    paths=[p for p in (TRIAL/'cases').rglob('*') if p.is_file()]
    output=dict(passed=True,success=step['success'],inputs=pair(folder),observations=seen,
        geometry=checked['geometry'],contact=checked['contact'],live_held=live,commands=commands,
        return_route=returning,physical_attempts=1,model_calls=0,identities={str(p):sha(p) for p in paths})
    save(TRIAL/'audit.json',output)
    print(dict(passed=True,success=step['success'],physical_attempts=1),flush=True)


if __name__=='__main__':
    main()

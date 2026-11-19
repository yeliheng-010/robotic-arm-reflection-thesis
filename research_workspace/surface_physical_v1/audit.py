import sys
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import top_runtime
import rb_audit
import sv_strategy_audit
from audit_v5 import audit_attempt
from action_space_audit_v1.scene import opened
from route_audit_v3 import rebuild
from cc_audit import visibility
from ta_audit import observations
from sr_audit import measured
from rh_audit import return_audit
from op_audit import live_check
from surface_physical_v1.common import TRIAL,PROJECT,STATIC,read,save,sha,verify,entry
from surface_physical_v1.replay import pair,candidate,replay


def preflight():
    case=entry()['case']
    folder=TRIAL/'preflight'
    source=read(STATIC/'manifest.json')
    points=np.asarray(read(PROJECT/'model_grasp_gpu_v1/observation.json')['target_points'])
    with patch.object(top_runtime,'candidates',candidate()),opened(source) as flow, \
         top_runtime.filter_context(points,{}):
        plan,strict=replay(flow,case,hooks=(grasp.move_to_grasp_pose,grasp.move_to_point))
    assert plan==read(folder/'actual_plan.json')
    assert strict==read(folder/'strict_held_precheck.json')
    seen=visibility(folder/'initial_visibility.json',case['config'])
    assert seen['accepted'] and read(folder/'bridge.json')['planners']==[]
    assert not (folder/'step.json').exists()
    checked=pair(folder)
    result=dict(passed=strict['passed'],audit_verified=True,independent=True,
        inputs=checked,initial_visibility=seen,strict_held=strict,physical_attempts=0)
    save(TRIAL/'preflight_audit.json',result)
    print(dict(preflight_audit_passed=result['passed'],physical_attempts=0),flush=True)


def geometry(case,trace):
    flow=rebuild(case,trace)
    plan,strict=replay(flow,case,hooks=(grasp.move_to_grasp_pose,grasp.move_to_point))
    for key,value in plan.items():
        assert trace[key]==value,key
    assert strict['passed']
    return dict(passed=True,selected=True,full_search_repeated=True,strict_held=strict,independent=True)


def lifecycle(folder):
    value=read(folder/'lifecycle.json')
    assert value['released'] and value['actual_close_calls']==1 and value['close_error'] is None
    return value


def complete(folder,case):
    step=read(folder/'step.json')
    result=read(folder.parent/'result.json')
    assert result['manifest_sha256']==sha(TRIAL/'manifest.json')
    assert result['physical_attempts']==step['index']==1
    assert read(folder/'approved_plan_match.json')['actual_plan_identical']
    seen=observations(case,folder)
    assert result['public_input_allowed']==seen['final']['accepted']
    with patch.object(top_runtime,'candidates',candidate()),patch.object(rb_audit,'geometry',geometry), \
         patch.object(sv_strategy_audit,'audit_attempt',audit_attempt):
        checked=sv_strategy_audit.inspect(case,step)
    live=live_check(case,folder)
    returning=return_audit(case,folder) if (folder/'return_plan.json').exists() else None
    assert step['success']==result['new_success']
    if step['success']:
        assert live['entered'] and live['feasible'] and returning is not None
    return dict(passed=True,success=step['success'],inputs=pair(folder),observations=seen,
        geometry=checked['geometry'],contact=checked['contact'],live_held=live,return_route=returning,
        lifecycle=lifecycle(folder),physical_attempts=1,model_calls=0,training_eligible=False)


def physical():
    verify(TRIAL/'execution_manifest.json')
    case=entry()['case']
    folder=TRIAL/'cases'/str(case['item']['seed'])/'first'
    if not (folder/'step.json').exists():
        contacts=measured(folder)
        contacts.pop('closing_end',None)
        output=dict(audit_completed=True,status='partial_execution',task_success=None,
            physical_attempts_consumed=1,contacts=contacts,lifecycle=lifecycle(folder),
            outcome=read(TRIAL/'execution_outcome.json'),training_eligible=False)
        save(TRIAL/'partial_audit.json',output)
        print(dict(status='partial_execution',task_success=None),flush=True)
        return
    result=complete(folder,case)
    verify(TRIAL/'execution_manifest.json')
    files=[p for p in (TRIAL/'cases').rglob('*') if p.is_file()]
    result['identities']={str(p):sha(p) for p in files}
    save(TRIAL/'audit.json',result)
    print(dict(audited=True,success=result['success'],physical_attempts=1),flush=True)


if __name__=='__main__':
    {'preflight':preflight,'physical':physical}[sys.argv[1]]()

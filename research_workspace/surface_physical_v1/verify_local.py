"""只核验同步证据与量化接触时序，不运行仿真或重写旧结果。"""
from pathlib import Path
import json
import numpy as np
from surface_grasp_v1.common import read,save,sha

ROOT=Path(__file__).resolve().parent
REVISION=ROOT.parent/'surface_physical_audit_v2'
REMOTE=ROOT/'evidence/remote'
FIXED=REVISION/'evidence/remote'
FOLDER=REMOTE/'trial/cases/964347/first'


def files():
    count=0
    for root in (ROOT,REVISION):
        for row in read(root/'LOCAL_DELIVERY.json')['entries']:
            assert sha(root/'evidence/remote'/row['path'])==row['sha256'],row['path']
            count+=1
    manifest=read(REMOTE/'trial/manifest.json')
    prefix='/home/yeliheng/grasp_server/surface_physical_v1/'
    sources=[(Path(n.removeprefix(prefix)),h) for n,h in manifest['identities'].items() if n.startswith(prefix)]
    for path,digest in sources:
        assert sha(ROOT/path)==digest,path
    for row in read(ROOT/'IMAGE_DELIVERY.json')['entries']:
        assert sha(REMOTE/row['path'])==row['sha256']
    revised=[p for p in FIXED.iterdir() if p.suffix in ('.py','.sbatch')]
    for path in revised:
        assert sha(REVISION/path.name)==sha(path),path
    return dict(text_files=count,original_source_files=len(sources),revised_source_files=len(revised),images=2)


def local_center(row):
    tcp=np.asarray(row['tcp'])
    return tcp[:3,:3].T@(np.asarray(row['source'])-tcp[:3,3])


def facts():
    rows=[json.loads(line) for line in (FOLDER/'contacts.jsonl').read_text(encoding='utf-8').splitlines()]
    carry=[row for row in rows if row['action']=='move_to_point']
    both=sum('PurpleCapsule' in r['pads']['left'] and 'PurpleCapsule' in r['pads']['right'] for r in carry)
    start,end=carry[0],carry[-1]
    prediction=read(FOLDER/'actual_plan.json')['selected']['goal']['object_center']
    record=read(FOLDER/'execution/result.json')['records'][0]
    guard=read(FOLDER/'guard.json')
    result=dict(source_sha256=sha(FOLDER/'contacts.jsonl'),contact_samples=len(rows),
        carry_samples=len(carry),both_pad_carry_samples=both,
        source_relative_tcp_start_m=local_center(start).tolist(),
        source_relative_tcp_end_m=local_center(end).tolist(),
        relative_center_drift_m=float(np.linalg.norm(local_center(end)-local_center(start))),
        pre_release_center_prediction_error_m=float(np.linalg.norm(np.asarray(end['source'])-prediction)),
        tcp_release_xy_error_m=guard['release']['xy_error_m'],
        final_object_xy_error_m=record['evaluation']['xy_error_m'],
        failure_type=record['error']['error_type'],final_contained_xy=record['evaluation']['inside_xy'],
        final_visibility_rejected=read(FOLDER/'observations/visibility_0.json')['gate']['rejected'],
        private_ground_truth_audit_only=True,
        limitation='Sampled bilateral contact is not a fixed object-to-gripper transform or continuous-time proof')
    assert len(rows)==1077 and both==len(carry)==227
    assert guard['release_checked'] and guard['open_called']
    assert result['failure_type']=='object_outside_container' and not result['final_contained_xy']
    return result


def outcome(result):
    assert result['passed'] and result['success'] is False
    assert result['physical_attempts']==1 and result['additional_physical_attempts']==0
    assert result['contact']['self_contact_samples']==0 and result['live_held']['feasible']
    assert result['return_route']['command_samples_identical']
    assert result['lifecycle']['actual_close_calls']==1 and result['lifecycle']['close_error'] is None
    assert not result['training_eligible'] and result['model_calls']==0


def audit():
    for name in ('preflight_result.json','preflight_audit.json'):
        result=read(REMOTE/'trial'/name)
        assert result['passed'] and result['physical_attempts']==0
    result=read(FIXED/'audit.json')
    outcome(result)
    prefix='/home/yeliheng/grasp_server/surface_physical_v1/'
    for name,digest in result['identities'].items():
        path=REMOTE/name.removeprefix(prefix)
        if path.exists():
            assert sha(path)==digest,name
    assert read(REMOTE/'trial/attempt_claim.json')['physical_attempt_budget_consumed']==1
    states=[line.split() for line in (FIXED/'scheduler_final.txt').read_text().splitlines()]
    states={row[0]:row[1:3] for row in states}
    for job in ('6485','6487','6488'):
        assert states[job]==['COMPLETED','0:0']
    assert states['6486']==['FAILED','1:0']
    return dict(independent_physical_audit_passed=True,physical_task_success=False,
        physical_attempts=1,model_calls=0,training_runs=0,training_eligible=False,
        original_audit_failed=True,read_only_revised_audit_passed=True)


if __name__=='__main__':
    result=dict(passed=True,**files(),**audit(),facts=facts())
    save(ROOT/'FINAL_VERIFICATION.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

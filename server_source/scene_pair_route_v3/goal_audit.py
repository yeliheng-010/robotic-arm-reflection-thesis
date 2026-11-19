import os
import json
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read,save,sha
from pair_run import audit_sensor
from goal_inputs import ROOT
from goal_prepare import verify
from goal_audit_geometry import audit as audit_geometry


def execution(record, trace, *, guard, rows):
    selected=trace['selected']
    assert trace['active'] and guard['strict_contacts']
    if selected is None:
        assert record['error']['evidence']['route_planning_rejected']
        assert not rows and not guard['open_called']
        return
    assert record['approach_plan']['route_id']==selected['id']
    assert record['approach_plan']['q1']==selected['q1']
    adapter=record['execution_adapter']
    if adapter:
        np.testing.assert_allclose(selected['target'],adapter['target_xyz'],atol=1e-12,rtol=0)
        assert adapter['lift_height']==selected['lift']
        duration=1. if selected['transport_route']=='direct' else 2.
        assert adapter['durations']==[0.,1.,duration,1.]
        np.testing.assert_allclose(selected['target'],np.array(adapter['planned_poses'][-1])[:3,3],atol=1e-12)
    if guard['release_checked']:
        np.testing.assert_allclose(selected['target'],guard['release']['expected'],atol=1e-12)


def physical(case):
    folder=ROOT/'physics'/case['id']
    result=read(folder/'result.json')
    assert len(result['steps'])==3 and result['steps'][:2]==case['steps']
    step=result['steps'][-1]
    assert step['index']==3 and step['state']==case['steps'][-1]['state']
    assert result['manifest_sha256']==sha(ROOT/'manifest.json')
    for name in ('route','guard'):
        assert sha(folder/(name+'.json'))==result[name+'_sha256']
    assert sha(folder/'contacts.jsonl')==result['trace_sha256']
    assert sha(step['result_path'])==step['result_sha256']
    record=read(step['result_path'])['records'][0]
    before=read(case['steps'][0]['result_path'])['records'][0]
    for key in ('initial_qpos','initial_body_xyz'):
        np.testing.assert_array_equal(before['candidate_trace'][key],record['candidate_trace'][key])
    assert record['parameters']==step['state']['parameters']
    sensor=audit_sensor(record['domain_randomization']['sensor_frames'],case['config'],index=3)
    trace,guard=read(folder/'route.json'),read(folder/'guard.json')
    geometry=audit_geometry(case,trace)
    rows=[json.loads(s) for s in (folder/'contacts.jsonl').read_text().splitlines()]
    execution(record,trace,guard=guard,rows=rows)
    success=bool(record['physical_success'])
    assert success==step['success']==result['success']
    if success:
        assert guard['release_checked'] and guard['open_called'] and guard['reason'] is None
    return dict(success=success,new_attempts=1,sensor=sensor,geometry=geometry,guard=guard,
                error=(record['error'] or {}).get('error_type'),evaluation=record['evaluation'],
                trace_samples=len(rows),stop_time=rows[-1]['time'] if rows else None)


def inspect(case, selected):
    for step in case['steps']:
        assert sha(step['result_path'])==step['result_sha256']
    if case['reused_success']:
        assert case['steps'][0]['success'] and case['steps'][0]['feedback'] is None
        return dict(id=case['id'],success=True,shared=True,new_attempts=0)
    plan=read(ROOT/('preflight_'+case['id']+'.json'))
    summary=next(r for r in read(ROOT/'preflight.json')['rows'] if r['id']==case['id'])
    assert summary['sha256']==sha(ROOT/('preflight_'+case['id']+'.json'))
    geometry=audit_geometry(case,plan)
    row=dict(id=case['id'],shared=False,preflight=geometry,endpoint_passing=plan['endpoints']['passing'])
    if case['id'] in selected:
        assert plan['selected'] is not None
        row.update(physical(case))
    else:
        assert plan['selected'] is None
        row.update(success=False,new_attempts=0,status=plan['status'])
    return row


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest=verify()
    assert read(ROOT/'run_complete.json')['manifest_sha256']==sha(ROOT/'manifest.json')
    rows=[inspect(c,manifest['selected']) for c in manifest['cases']]
    verify()
    result=dict(passed=True,rows=rows,shared_successes=7,actual_new_attempts=sum(r['new_attempts'] for r in rows),
                gains=sum(r['success'] and not r['shared'] for r in rows),promotion_allowed=False,
                full_48_conditions_rerun=False,manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'verification.json',result)
    print({k:v for k,v in result.items() if k!='rows'},flush=True)


if __name__=='__main__':
    main()

"""共享前缀、第三次预算、实际观测和执行后果审计。"""
import json
import os
from collections import Counter
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read, save, sha
from pair_run import audit_sensor
from waypoint_inputs import ROOT
from waypoint_prepare import verify
from waypoint_audit_search import audit as audit_search
from waypoint_policy import allowed


def audit_physics(case):
    folder = ROOT/'physics'/case['id']
    result = read(folder/'result.json')
    assert len(result['steps']) == 3 and result['steps'][:2] == case['steps']
    step = result['steps'][-1]
    assert step['index'] == 3 and step['state'] == case['steps'][-1]['state']
    assert result['manifest_sha256'] == sha(ROOT/'manifest.json')
    for name in ('route','guard'):
        assert sha(folder/(name+'.json')) == result[name+'_sha256']
    assert sha(folder/'contacts.jsonl') == result['trace_sha256']
    assert sha(step['result_path']) == step['result_sha256']
    record = read(step['result_path'])['records'][0]
    before = read(case['steps'][0]['result_path'])['records'][0]
    for name in ('initial_qpos','initial_body_xyz'):
        np.testing.assert_array_equal(before['candidate_trace'][name],record['candidate_trace'][name])
    assert record['parameters'] == step['state']['parameters']
    assert record['domain_randomization']['level'] == case['config']['group']
    sensor = audit_sensor(record['domain_randomization']['sensor_frames'],case['config'],index=3)
    trace, guard = read(folder/'route.json'), read(folder/'guard.json')
    assert trace['active'] and guard['strict_contacts']
    static = audit_search(case,trace)
    selected = trace['selected']
    rows = [json.loads(line) for line in (folder/'contacts.jsonl').read_text().splitlines()]
    execution(record, selected, guard=guard, rows=rows)
    if step['success']:
        assert guard['release_checked'] and guard['open_called'] and guard['reason'] is None
    return dict(success=step['success'], error=(record['error'] or {}).get('error_type'),
                selected=(selected or {}).get('id'), sensor=sensor, static=static, guard=guard,
                trace_samples=len(rows), new_attempts=1, result_sha256=step['result_sha256'])


def execution(record, selected, *, guard, rows):
    if selected is None:
        assert record['error']['evidence']['route_planning_rejected'] and not guard['open_called']
        assert not rows and record['approach_plan'] == {} and record['execution_adapter'] == {}
    else:
        assert record['approach_plan']['route_id'] == selected['id']
        assert record['approach_plan']['q1'] == selected['q1']
        adapter = record['execution_adapter']
        if adapter:
            assert adapter['lift_height'] == selected['lift']
            transport_time = 1. if selected['transport_route']=='direct' else 2.
            assert adapter['durations'] == [0.,1.,transport_time,1.]
            np.testing.assert_allclose(selected['target'],adapter['target_xyz'],atol=1e-12,rtol=0)


def inspect_case(case, selected):
    for step in case['steps']:
        assert sha(step['result_path']) == step['result_sha256']
    if case['reused_success']:
        assert case['steps'][0]['success'] and case['steps'][0]['feedback'] is None
        return dict(id=case['id'],success=True,shared_success=True,new_attempts=0)
    prior = read(case['steps'][-1]['result_path'])['records'][0]
    assert allowed(prior,read(case['prior_trace']),case['item']['destination'])
    plan_path = ROOT/('preflight_'+case['id']+'.json')
    plan = read(plan_path)
    summary = next(r for r in read(ROOT/'preflight.json')['rows'] if r['id']==case['id'])
    assert summary['sha256'] == sha(plan_path)
    static = audit_search(case,plan)
    result = dict(id=case['id'], shared_success=False, preflight=static,
                  prefix_count=len(plan['prefixes']), carry_count=len(plan['candidates']),
                  prefix_reasons=dict(Counter((r.get('failure') or {}).get('reason','passed') for r in plan['prefixes'])))
    if case['id'] in selected:
        assert plan['selected'] is not None
        result.update(audit_physics(case))
    else:
        assert plan['selected'] is None
        result.update(success=False,new_attempts=0,status='static_search_exhausted')
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    assert read(ROOT/'run_complete.json')['manifest_sha256'] == sha(ROOT/'manifest.json')
    rows = [inspect_case(c,manifest['selected']) for c in manifest['cases']]
    verify()
    result = dict(passed=True,rows=rows,shared_successes=7,actual_new_attempts=sum(r['new_attempts'] for r in rows),
                  gains=sum(r['success'] and not r['shared_success'] for r in rows),
                  promotion_allowed=False,full_48_conditions_rerun=False,
                  manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'verification.json',result)
    print({k:v for k,v in result.items() if k!='rows'},flush=True)


if __name__ == '__main__':
    main()

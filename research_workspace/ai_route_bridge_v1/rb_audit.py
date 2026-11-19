import argparse
from pathlib import Path
import numpy as np
from nc_audit_attempt import audit as attempt
from nc_audit_frames import view
from goal_audit_geometry_v2 import audit as geometry
from dr_audit import recovery
from rb_common import ROOT, read, save, sha, verify, change


def route(case, step, record):
    folder = Path(step['session_path'])
    trace = read(folder/'route.json')
    assert trace['active'] == step['state']['parameters']['replan']
    assert trace['requested'] == step['state']['parameters']
    if not trace['active']:
        assert 'depth_recovery' not in record
        return dict(active=False)
    recovery(step)
    if 'selected' not in trace:
        assert not read(folder/'bridge.json')['planners']
        return dict(active=True, entered_planner=False)
    result = geometry(case, trace)
    selected = trace['selected']
    if selected is not None:
        assert selected['lift'] == step['state']['parameters']['lift_height']
        assert record['approach_plan']['route_id'] == selected['id']
        if record['execution_adapter']:
            adapter = record['execution_adapter']
            np.testing.assert_allclose(selected['target'], adapter['target_xyz'], atol=1e-12, rtol=0)
            assert adapter['lift_height'] == selected['lift']
        guard = read(folder/'guard.json')
        if guard['release_checked']:
            np.testing.assert_allclose(selected['target'], guard['release']['expected'], atol=1e-12, rtol=0)
    return dict(active=True, geometry=result)


def inspect(case):
    folder = ROOT/'cases'/case['item']['id']
    result = read(folder/'result.json')
    if result['status'] == 'geometry_rejected':
        assert not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']
        assert result['steps'] == result['actions'] == result['observations'] == []
        return dict(id=case['item']['id'], status='geometry_rejected', attempts=0, success=False)
    assert result['manifest_sha256'] == sha(ROOT/'manifest.json') and result['model_calls'] == 0
    steps = result['steps']
    assert 1 <= len(steps) <= 3 and steps[0]['state'] == case['state']
    assert len(result['actions']) == len(steps)-1 and len(result['observations']) == len(steps)
    rows = []
    for index, step in enumerate(steps, 1):
        assert step['index'] == index
        record, _, _ = attempt(case, step)
        summary = view(result['observations'][index-1], case)
        assert len(summary['paths']) == 1 and summary['remaining'] == 0
        if index > 1:
            action = 'SAFE_ROUTE' if index == 2 else 'SLOW_ROUTE'
            assert result['actions'][index-2] == dict(after_attempt=index-1, action=action)
            assert not steps[index-2]['success'] and step['state'] == change(steps[index-2]['state'], action)
        rows.append(dict(index=index, success=step['success'], route=route(case, step, record)))
    assert result['success'] == steps[-1]['success']
    return dict(id=case['item']['id'], attempts=len(steps), success=result['success'], rows=rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    cases = [c for c in verify()['cases'] if c['item']['seed']==args.seed]
    assert len(cases) == 4
    rows = [inspect(c) for c in cases]
    verify()
    artifacts = [p for c in cases for p in (ROOT/'cases'/c['item']['id']).rglob('*') if p.is_file()]
    save(ROOT/f'audit_{args.seed}.json', dict(passed=True, rows=rows, training_ready=False,
        identities={str(p): sha(p) for p in artifacts}, manifest_sha256=sha(ROOT/'manifest.json')))
    print(rows, flush=True)


if __name__ == '__main__':
    main()

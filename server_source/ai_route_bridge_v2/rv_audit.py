import argparse
from pathlib import Path
from rv_common import ROOT, read, save, sha, verify, change
from nc_audit_attempt import audit as attempt
from nc_audit_frames import view
from rb_audit import route
from cp_audit import candidate_audit
from rv_runtime import mode


def inspect(case):
    folder = ROOT/'cases'/case['item']['id']
    result = read(folder/'result.json')
    if result['status'] == 'geometry_rejected':
        assert not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']
        assert result['steps'] == result['actions'] == result['observations'] == []
        return dict(id=case['item']['id'], attempts=0, success=False, status='geometry_rejected')
    assert result['manifest_sha256'] == sha(ROOT/'manifest.json') and result['model_calls'] == 0
    steps = result['steps']
    assert 1 <= len(steps) <= 3 and len(result['actions']) == len(steps)-1
    assert len(result['observations']) == len(steps)
    expected_state, expected_control = case['state'], dict(grasp_mode='original')
    rows = []
    for index, step in enumerate(steps, 1):
        assert step['index'] == index and step['state'] == expected_state and step['control'] == expected_control
        assert read(Path(step['session_path'])/'control.json') == expected_control
        record, _, _ = attempt(case, step)
        summary = view(result['observations'][index-1], case)
        assert len(summary['paths']) == 1 and summary['remaining'] == 0
        with mode(expected_control):
            checked = route(case, step, record)
        if step['state']['parameters']['replan']:
            candidate_audit(step, case['config'])
        rows.append(dict(index=index, success=step['success'], control=expected_control, route=checked))
        if index < len(steps):
            assert not step['success']
            action = 'SAFE_ROUTE' if index == 1 else 'WORLD_DOWN_ROUTE'
            assert result['actions'][index-1] == dict(after_attempt=index, action=action)
            expected_state, expected_control = change(expected_state, expected_control, action=action)
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

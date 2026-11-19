from reflection.__main__ import bootstrap
bootstrap()
import argparse
import json
from pathlib import Path
from sr_common import ROOT, read, save, sha, verify, change, ACTIONS
from nc_audit_attempt import audit as attempt
from nc_audit_frames import view
from rb_audit import route
from cp_audit import candidate_audit
from rv_runtime import mode
from self_geometry import context, forbidden


def measured(folder):
    rows = [json.loads(s) for s in (folder/'contacts.jsonl').read_text().splitlines()]
    hits = [c for r in rows for c in r['contacts'] if forbidden(c['roots'], c['distance'])]
    end = [r for r in rows if r['action']=='close_gripper' and r['event']=='end_or_abort']
    return dict(samples=len(rows), self_contact_samples=sum(any(forbidden(c['roots'],c['distance'])
        for c in r['contacts']) for r in rows), max_self_force=max((abs(c['force'][0]) for c in hits),default=0.),
        closing_end=end[-1] if end else None)


def inspect(case):
    folder = ROOT/'cases'/case['item']['id']
    result = read(folder/'result.json')
    if result['status']=='geometry_rejected':
        assert not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']
        return dict(id=case['item']['id'], attempts=0, success=False, status='geometry_rejected')
    assert result['manifest_sha256']==sha(ROOT/'manifest.json') and result['model_calls']==0
    steps = result['steps']
    assert 1<=len(steps)<=3 and len(result['actions'])==len(steps)-1
    assert len(result['observations'])==len(steps)
    state, control, rows = case['state'], dict(grasp_mode='original'), []
    for index, step in enumerate(steps, 1):
        assert step['index']==index and step['state']==state and step['control']==control
        with context(), mode(control):
            record, _, _ = attempt(case, step)
            checked = route(case, step, record)
        summary = view(result['observations'][index-1], case)
        assert len(summary['paths'])==1 and summary['remaining']==0
        if state['parameters']['replan']:
            candidate_audit(step, case['config'])
        evidence = measured(Path(step['session_path']))
        save(Path(step['session_path'])/'contact_summary.json', evidence)
        rows.append(dict(index=index, success=step['success'], route=checked,
                         contacts={k:v for k,v in evidence.items() if k!='closing_end'}))
        if index<len(steps):
            assert not step['success']
            assert result['actions'][index-1]==dict(after_attempt=index, action=ACTIONS[index-1])
            state, control = change(state, control, action=ACTIONS[index-1])
    assert result['success']==steps[-1]['success']
    return dict(id=case['item']['id'], attempts=len(steps), success=result['success'], rows=rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    cases = [c for c in verify()['cases'] if c['item']['seed']==args.seed]
    assert len(cases)==4
    rows = [inspect(c) for c in cases]
    files = [p for c in cases for p in (ROOT/'cases'/c['item']['id']).rglob('*') if p.is_file()]
    save(ROOT/f'audit_{args.seed}.json', dict(passed=True, rows=rows, training_ready=False,
        identities={str(p):sha(p) for p in files}, manifest_sha256=sha(ROOT/'manifest.json')))
    print([dict(id=r['id'], attempts=r['attempts'], success=r['success']) for r in rows], flush=True)


if __name__ == '__main__':
    main()

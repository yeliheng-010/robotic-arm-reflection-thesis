import os
from pathlib import Path
from collections import Counter
from policy import eligible, snapshot
from tp_common import ROOT, read, save, sha, verify, change, ACTIONS


def collect(case):
    name = case['item']['id']
    audited = read(ROOT/'audits'/(name+'.json'))
    assert audited['passed'] and audited['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert all(sha(p) == h for p,h in audited['identities'].items())
    result = read(ROOT/'cases'/name/'result.json')
    rows = []
    for index, entry in enumerate(result['actions']):
        before, following = result['steps'][index:index+2]
        state, strategy = change(before['state'], before['strategy'], action=entry['action'])
        assert state == following['state'] and strategy == following['strategy'] and not before['success']
        if entry['action'] == ACTIONS[0]:
            action = dict(id='SET_GRASP_STRATEGY', args=dict(value='observed_top'))
        else:
            action = dict(id='SET_TIME_SCALE', args=dict(value=3.))
        record = read(before['result_path'])['records'][0]
        allowed, reason = eligible(record)
        summary = read(Path(before['session_path'])/'observation_summary.json')
        rows.append(dict(condition=name, seed=case['item']['seed'], snapshot_id=snapshot(case['item'], summary),
            action=action, before=before, successor=following, eligible_natural=allowed,
            private_eligibility_reason=reason, verified_recovery=allowed and following['success']))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID') and read(ROOT/'complete.json')['passed']
    rows = [r for case in verify()['cases'] for r in collect(case)]
    natural = [r for r in rows if r['eligible_natural']]
    recovered = [r for r in natural if r['verified_recovery']]
    summary = dict(decisions=len(rows), unique_natural_snapshots=len({r['snapshot_id'] for r in natural}),
        verified_natural_recoveries=len({r['snapshot_id'] for r in recovered}),
        correction_action_types=sorted({r['action']['id'] for r in recovered}),
        natural_seed_groups=sorted({r['seed'] for r in natural}), recovery_seed_groups=sorted({r['seed'] for r in recovered}),
        exclusions=dict(Counter(r['private_eligibility_reason'] for r in rows if not r['eligible_natural'])),
        pilot_is_training_data=False, training_ready=False)
    paths = [Path(__file__), ROOT/'complete.json', *list((ROOT/'audits').glob('*.json'))]
    save(ROOT/'inventory.json', dict(summary=summary, rows=rows, manifest_sha256=sha(ROOT/'manifest.json'),
        identities={str(p):sha(p) for p in paths}))
    print(summary, flush=True)


if __name__ == '__main__':
    main()

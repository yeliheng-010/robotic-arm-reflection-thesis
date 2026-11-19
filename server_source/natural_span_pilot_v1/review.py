import os
from pathlib import Path
from collections import Counter
from live_budget import apply_action
from policy import eligible, snapshot
from sp_common import ROOT, read, save, sha, verify, change, ACTIONS


def action(name):
    if name == ACTIONS[0]:
        return dict(id='SET_GRASP_OFFSET', args=dict(delta_m=[0., 0., -.03]))
    assert name == ACTIONS[1]
    return dict(id='SET_TIME_SCALE', args=dict(value=3.))


def collect(case):
    name = case['item']['id']
    audited = read(ROOT/'audits'/(name+'.json'))
    assert audited['passed'] and audited['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert all(sha(p) == h for p,h in audited['identities'].items())
    result = read(ROOT/'cases'/name/'result.json')
    rows = []
    for index, entry in enumerate(result['actions']):
        current, following = result['steps'][index:index+2]
        requested = action(entry['action'])
        assert not current['success'] and apply_action(current['state'], requested) == following['state']
        record = read(current['result_path'])['records'][0]
        allowed, reason = eligible(record)
        summary = read(Path(current['session_path'])/'observation_summary.json')
        rows.append(dict(condition=name, seed=case['item']['seed'], snapshot_id=snapshot(case['item'], summary),
            action=requested, before=current, successor=following, eligible_natural=allowed,
            private_eligibility_reason=reason, verified_recovery=allowed and following['success']))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID') and read(ROOT/'complete.json')['passed']
    manifest = verify()
    rows = [row for case in manifest['cases'] for row in collect(case)]
    natural = [r for r in rows if r['eligible_natural']]
    recovered = [r for r in natural if r['verified_recovery']]
    summary = dict(decisions=len(rows), unique_natural_snapshots=len({r['snapshot_id'] for r in natural}),
        verified_natural_recoveries=len({r['snapshot_id'] for r in recovered}),
        correction_action_types=sorted({r['action']['id'] for r in recovered}),
        natural_seed_groups=sorted({r['seed'] for r in natural}),
        recovery_seed_groups=sorted({r['seed'] for r in recovered}),
        exclusions=dict(Counter(r['private_eligibility_reason'] for r in rows if not r['eligible_natural'])),
        pilot_is_training_data=False, training_ready=False)
    save(ROOT/'inventory.json', dict(summary=summary, rows=rows, manifest_sha256=sha(ROOT/'manifest.json'),
        identities={str(p):sha(p) for p in [Path(__file__), ROOT/'complete.json', *list((ROOT/'audits').glob('*.json'))]}))
    print(summary, flush=True)


if __name__ == '__main__':
    main()

import os
from copy import deepcopy
from reflection.__main__ import bootstrap
bootstrap()
from pilot import extract_seeds
from sr_common import change as setup
from qp_common import verify as previous
from sv_common import ROOT, read, save, sha

SOURCE = ROOT.parent/'safe_visual_qualification_v2'
RESERVATION = ROOT.parent/'safe_visual_preflight_v1'
LIFT_M = .20


def validate_recovery(value):
    summary = value['summary']
    assert summary['verified_natural_recoveries'] >= 1, 'No verified natural recovery'
    rows = [r for r in value['rows'] if r['eligible_natural'] and r['verified_recovery']]
    assert len({r['snapshot_id'] for r in rows}) == summary['verified_natural_recoveries']
    assert all(not r['before']['success'] and r['successor']['success'] for r in rows)


def prerequisites():
    paths = [ROOT/'code_checks_v3/verification.json',
        ROOT.parent/'natural_span_pilot_v1/inventory.json', ROOT.parent/'ai_visual_service_v1/audit.json']
    checked, recovery, visual = [read(p) for p in paths]
    assert checked['passed'] and visual['passed'] and visual['model_calls'] == 4
    validate_recovery(recovery)
    identities = dict(previous()['identities'])
    for value in (checked, recovery, visual):
        assert all(sha(p) == h for p, h in value['identities'].items())
        identities.update(value['identities'])
    identities.update({str(p):sha(p) for p in paths})
    return identities, checked


def qualified_cases(reserved, result):
    decisions = {r['id']:r for r in result['rows']}
    cases = []
    for original in reserved['cases']:
        case = deepcopy(original)
        row = decisions[case['item']['id']]
        if not row['passed']:
            continue
        assert row['lift_height'] == LIFT_M and sha(row['path']) == row['sha256']
        assert all(r['passed'] for r in row['projection'].values())
        case['qualification'] = row
        case['item']['id'] = 'A'+case['item']['id'][1:]
        case['item']['split'] = 'safe_visual_loop_pilot_not_training'
        case['state'], case['control'] = setup(case['state'], dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        case['state']['parameters']['lift_height'] = LIFT_M
        cases.append(case)
    assert cases
    return cases


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    identities, checked = prerequisites()
    reserved, result = read(SOURCE/'manifest.json'), read(SOURCE/'result.json')
    assert reserved['seeds'] == read(RESERVATION/'manifest.json')['seeds']
    assert all(sha(p) == h for p,h in reserved['identities'].items())
    identities.update(reserved['identities'])
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths-{SOURCE/'manifest.json', RESERVATION/'manifest.json'}:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(reserved['seeds'])
    cases = qualified_cases(reserved, result)
    files = [SOURCE/'manifest.json', SOURCE/'result.json']
    files += list((ROOT.parent/'ai_visual_service_v1').glob('vs_*.py'))
    files += [ROOT.parent/'ai_visual_input_v1/mm_generator.py']
    files += [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md')]
    identities.update({str(p):sha(p) for p in files})
    save(ROOT/'manifest.json', dict(cases=cases, identities=identities, seeds=reserved['seeds'],
        max_new_attempts=7*len(cases), max_model_calls=8*len(cases), max_attempts_per_trajectory=3,
        max_extra_observations=2, tests=checked['tests'], training_ready=False,
        qualification_rows=result['rows'], seed_isolation=dict(reservation_only_reuse=True, overlap=False)))
    print(dict(conditions=len(cases), max_new_attempts=7*len(cases), max_model_calls=8*len(cases)), flush=True)


if __name__ == '__main__':
    main()

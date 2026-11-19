import os
from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from pilot import extract_seeds
from sr_common import change as setup
from qp_common import verify as previous
from sv_common import ROOT, SOURCE, read, save, sha


def prerequisites():
    checked = read(ROOT/'code_checks/verification.json')
    assert checked['passed'] and all(sha(p) == h for p,h in checked['identities'].items())
    paths = [ROOT.parent/'natural_deeper_pilot_v1/inventory.json', ROOT.parent/'ai_visual_service_v1/audit.json']
    recovery, visual = [read(p) for p in paths]
    assert recovery['summary']['verified_natural_recoveries'] >= 1
    assert visual['passed'] and visual['model_calls'] == 4
    for value in (recovery, visual):
        assert all(sha(p) == h for p,h in value['identities'].items())
    return {str(p):sha(p) for p in paths}, checked


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    identities, checked = prerequisites()
    identities.update(previous()['identities'])
    reserved, result = read(SOURCE/'manifest.json'), read(SOURCE/'result.json')
    assert all(sha(p) == h for p,h in reserved['identities'].items())
    identities.update(reserved['identities'])
    used = set()
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    for path in paths-{SOURCE/'manifest.json'}:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(reserved['seeds'])
    decisions = {r['id']:r for r in result['rows']}
    cases = []
    for case in reserved['cases']:
        row = decisions[case['item']['id']]
        if row['passed']:
            assert sha(row['path']) == row['sha256']
            case['qualification'] = row
            case['item']['id'] = 'A'+case['item']['id'][1:]
            case['item']['split'] = 'safe_visual_loop_pilot_not_training'
            case['state'], case['control'] = setup(case['state'], dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
            cases.append(case)
    identities.update(checked['identities'])
    files = [SOURCE/'manifest.json', SOURCE/'result.json', ROOT/'code_checks/verification.json']
    files += list((ROOT.parent/'ai_visual_service_v1').glob('vs_*.py'))
    files += [ROOT.parent/'ai_visual_input_v1/mm_generator.py']
    identities.update({str(p):sha(p) for p in files})
    save(ROOT/'manifest.json', dict(cases=cases, identities=identities, seeds=reserved['seeds'],
        max_new_attempts=7*len(cases), max_model_calls=8*len(cases), max_attempts_per_trajectory=3,
        max_extra_observations=2, tests=checked['tests'], training_ready=False,
        qualification_rows=result['rows'], seed_isolation=dict(reservation_only_reuse=True, overlap=False)))
    print(dict(conditions=len(cases), max_new_attempts=7*len(cases), max_model_calls=8*len(cases)), flush=True)


if __name__ == '__main__':
    main()

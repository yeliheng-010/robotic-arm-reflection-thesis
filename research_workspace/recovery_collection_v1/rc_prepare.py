import os
from copy import deepcopy
from reflection.__main__ import bootstrap
bootstrap()
from sr_common import change
from collection_common import ROOT, PARENT, BATCH, QUAL, PHYSICS, read, save, sha, verify


def main():
    assert os.environ.get('SLURM_JOB_ID')
    protocol = verify(ROOT/'protocol.json')
    reserved = verify(QUAL/'manifest.json')
    result = verify(QUAL/'result.json')
    assert result['manifest_sha256'] == sha(QUAL/'manifest.json')
    decisions = {r['id']:r for r in result['rows']}
    assert set(decisions) == {c['item']['id'] for c in reserved['cases']}
    cases = []
    for original in reserved['cases']:
        row = decisions[original['item']['id']]
        if not row['passed']:
            continue
        assert row['lift_height'] == .20 and sha(row['path']) == row['sha256']
        case = deepcopy(original)
        case['state'], _ = change(case['state'], dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        case['state']['parameters']['lift_height'] = .20
        case.update(control=dict(grasp_mode='world_down'), strategy='original', qualification=row)
        cases.append(case)
    identities = dict(reserved['identities'], **protocol['identities'])
    files = [QUAL/'manifest.json', QUAL/'result.json', *ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in files})
    save(PHYSICS/'manifest.json', dict(cases=cases, batch=BATCH, seeds=reserved['seeds'],
        qualification_rows=result['rows'], identities=identities, max_attempts=7*len(cases),
        max_model_calls=0, training_ready=False, protocol_sha256=sha(ROOT/'protocol.json')))
    print(dict(qualified=len(cases), proposed=len(reserved['cases']), max_attempts=7*len(cases)), flush=True)


if __name__ == '__main__':
    main()

"""消费前核查开发种子；预留不等于已执行。"""
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_prepare
from collection_common import split
from sr_common import change
from fa_common import ROOT, PARENT, RUN, SEEDS, read, save, sha, verify


def contains_seed(value):
    if isinstance(value, dict):
        return any(contains_seed(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_seed(v) for v in value)
    return type(value) is int and value in SEEDS


def isolation():
    patterns = ('*/manifest.json', '*/protocol.json', '*/*/manifest.json',
                'recovery_collection_v1/batches/*/*/manifest.json')
    paths = sorted(set(p for pattern in patterns for p in PARENT.glob(pattern)))
    allowed = PARENT/'recovery_collection_v1/protocol.json'
    hits = [p for p in paths if contains_seed(read(p))]
    assert hits == [allowed], hits
    assert all(split(seed) == 'dev' for seed in SEEDS)
    assert not (PARENT/'recovery_collection_v1/batches/010').exists()
    return dict(scanned={str(p): sha(p) for p in paths}, hits=[str(p) for p in hits],
                reserved_only=True, consumed=False, split='dev')


def main():
    assert not RUN.exists()
    source = PARENT/'return_home_v1/repair'
    prior = verify(source/'manifest.json')
    result = read(source/'result.json')
    assert result['complete'] and result['successes'] == 5
    isolated = isolation()
    with patch.object(nc_prepare, 'SEEDS', SEEDS):
        cases = nc_prepare.cases()
    for case in cases:
        case['item']['id'] = 'F'+case['item']['id'][1:]
        case['item']['split'] = 'dev'
        case['state'], _ = change(case['state'], dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        case['state']['parameters']['lift_height'] = .20
        case.update(control=dict(grasp_mode='world_down'), strategy='original')
    identities = dict(prior['identities'])
    files = [source/'manifest.json', source/'result.json', *ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch')]
    identities.update({str(p): sha(p) for p in files})
    save(RUN/'manifest.json', dict(cases=cases, identities=identities, seeds=list(SEEDS),
        seed_isolation=isolated, max_attempts=16, attempts_per_policy_condition=1,
        max_model_calls=0, training_updates=0, baseline_execution=False, final_test_used=False))
    print(dict(registered=8, seeds=SEEDS, max_attempts=16), flush=True)


if __name__ == '__main__':
    main()

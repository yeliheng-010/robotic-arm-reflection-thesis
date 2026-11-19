import os
from reflection.__main__ import bootstrap
bootstrap()
from pilot import extract_seeds
from collection_common import ROOT, PARENT, MAX_BATCHES, read, save, sha, seeds, split


def main():
    assert os.environ.get('SLURM_JOB_ID')
    checked = read(ROOT/'verification.json')
    assert checked['passed'] and all(sha(p) == h for p,h in checked['identities'].items())
    visual = read(PARENT/'visual_data_review_v1/inventory.json')
    assert visual['summary']['verified_natural_recoveries'] >= 1
    assert all(sha(p) == h for p,h in visual['identities'].items())
    paths = set(PARENT.glob('*/manifest.json')) | set(PARENT.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    reserved = [s for batch in range(MAX_BATCHES) for s in seeds(batch)]
    assert not used.intersection(reserved)
    sources = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md']
    sources.append(PARENT/'visual_data_review_v1/inventory.json')
    inherited = read(PARENT/'ai_safe_visual_loop_v1/manifest.json')['identities']
    continuation = read(PARENT/'ai_safe_visual_loop_v1/complete.json')
    assert continuation['passed']
    inherited.update(continuation['identities'])
    assert all(sha(p) == h for p,h in inherited.items())
    inherited.update({str(p):sha(p) for p in sources})
    save(ROOT/'protocol.json', dict(seeds=reserved, split_by_seed={str(s):split(s) for s in reserved},
        max_batches=MAX_BATCHES, max_attempts_per_condition=7, max_model_calls=0,
        minimum=dict(train_snapshots=120, train_seed_groups=24, dev_snapshots=40, dev_seed_groups=8,
            train_recoveries=40, train_recovery_seed_groups=12, correction_action_types=2),
        pilot_reuse=False, training_ready=False, scanned_manifests=len(paths),
        identities=inherited))
    print(dict(reserved=len(reserved), first_batch=seeds(0)), flush=True)


if __name__ == '__main__':
    main()

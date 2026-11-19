"""保持已登记布局/颜色/噪声，冻结相机可行性修正及拒绝轨迹。"""
from pathlib import Path
from copy import deepcopy
import unittest
import os
from sd_common import read, save, sha
from pv_protocol import verify
from sf_select import select
from sf_common import verify_source

ROOT = Path(__file__).resolve().parent


def selected(item, config, cache):
    source_path = ROOT.parent/'scene_pair_feasibility_v2'/'selection'/str(item['seed'])/'selection.json'
    original = read(source_path)
    cached = cache.setdefault(item['seed'], deepcopy(original['attempts']))
    result = select(config, ROOT/'selection'/item['id'],
                    bodies=(item['source'], item['destination']), cached=cached, original=original)
    return result, source_path


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    suite = unittest.defaultTestLoader.discover(str(ROOT), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful() and not (ROOT/'manifest.json').exists()
    previous = verify()
    source = verify_source()
    configs, selections, cache, evidence = {}, [], {}, {}
    items = [dict(row, split='used_seed_development') for row in previous['items']]
    for item in items:
        old = previous['configs'][f"{item['seed']}_{item['group']}"]
        if item['group'] == 'baseline':
            configs[item['id']] = old
            continue
        (config, selection), path = selected(item, old, cache)
        assert {k: v for k, v in config.items() if k not in ('camera', 'camera_accepted')} == {
            k: v for k, v in old.items() if k not in ('camera', 'camera_accepted')}
        configs[item['id']] = config
        evidence[str(path)] = sha(path)
        selections.append(dict(id=item['id'], seed=item['seed'], accepted=selection['accepted'],
                               proposals=len(selection['attempts'])))
        print('CAMERA', selections[-1], flush=True)
    paths = dict(previous['identities'])
    paths.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')})
    paths.update(evidence)
    paths[str(ROOT.parent/'scene_pair_feasibility_v2'/'manifest.json')] = source
    paths.update({str(p): sha(p) for p in (ROOT/'selection').rglob('*') if p.is_file()})
    save(ROOT/'manifest.json', dict(seeds=previous['seeds'], items=items, configs=configs,
         identities=paths, selection_summary=selections, source_manifest_sha256=sha(ROOT.parent/'scene_pair_validation_v1'/'manifest.json'),
         split='used_seed_development', test_used=False, training_approved=False, model_calls=0))
    save(ROOT/'preflight.json', dict(passed=True, tests=result.testsRun, complete=True,
         accounted=len(selections), accepted=sum(r['accepted'] for r in selections),
         manifest_sha256=sha(ROOT/'manifest.json')))
    print('FROZEN', selections, flush=True)


if __name__ == '__main__':
    main()

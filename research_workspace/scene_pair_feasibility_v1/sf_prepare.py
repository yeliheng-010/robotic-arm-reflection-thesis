"""保持已登记布局/颜色/噪声，冻结相机可行性修正及拒绝轨迹。"""
from pathlib import Path
import unittest
from sd_common import read, save, sha
from pv_protocol import verify
from sf_select import select

ROOT = Path(__file__).resolve().parent


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful() and not (ROOT/'manifest.json').exists()
    previous = verify()
    configs, selections = {}, []
    for seed in previous['seeds']:
        key = f'{seed}_varied_noisy'
        config, selection = select(previous['configs'][key], ROOT/'selection'/str(seed))
        for field in ('bodies', 'appearance', 'sensor'):
            assert config[field] == previous['configs'][key][field]
        configs[key] = config
        configs[f'{seed}_baseline'] = previous['configs'][f'{seed}_baseline']
        selections.append(dict(seed=seed, accepted=selection['accepted'], proposals=len(selection['attempts'])))
        print('CAMERA', selections[-1], flush=True)
    paths = dict(previous['identities'])
    paths.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')})
    items = [dict(row, split='used_seed_development') for row in previous['items']]
    save(ROOT/'manifest.json', dict(seeds=previous['seeds'], items=items, configs=configs,
         identities=paths, selection_summary=selections, source_manifest_sha256=sha(ROOT.parent/'scene_pair_validation_v1'/'manifest.json'),
         split='used_seed_development', test_used=False, training_approved=False, model_calls=0))
    save(ROOT/'preflight.json', dict(passed=True, tests=result.testsRun, complete=True,
         accounted=len(selections), accepted=sum(r['accepted'] for r in selections),
         manifest_sha256=sha(ROOT/'manifest.json')))
    print('FROZEN', selections, flush=True)


if __name__ == '__main__':
    main()

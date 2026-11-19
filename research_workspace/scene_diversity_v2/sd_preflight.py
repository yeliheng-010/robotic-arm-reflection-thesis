"""冻结前测试、独立编译检查和种子隔离。"""
import sys
import unittest
import numpy as np
from sd_config import ROOT, SEEDS, GROUPS, factors, items, MOVING
from sd_common import read, save, sha
from sd_inventory import inventory, root_boxes
from sd_scene import compiled
from sd_layout import sample, clear, fixed_boxes


def compiled_check(config, geometry):
    model, data = compiled(config)
    actual = root_boxes(model, data)
    occupied = fixed_boxes(geometry)
    failures = []
    for name in MOVING:
        if not clear(np.array(actual[name]), occupied, np.array(geometry['table'])):
            failures.append(name)
        occupied.append(np.array(actual[name]))
    for name, values in config.get('bodies', {}).items():
        np.testing.assert_allclose(values['position'], data.body(name).xpos, atol=1e-10)
    return dict(passed=not failures, failures=failures)


def unused():
    from pilot import extract_seeds
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths:
        if path == ROOT.parent/'scene_diversity_v1'/'manifest.json':
            previous = read(path)
            assert previous['seeds']==list(SEEDS)
            assert not (path.parent/'physics').exists(), 'Predecessor has physical results'
            continue
        used.update(extract_seeds(read(path)))
    assert not set(SEEDS)&used, 'Seed overlap with prior experiments'
    return len(paths)


def build(geometry):
    layouts, configs = {}, {}
    for seed in SEEDS:
        layout = sample(seed, geometry)
        layouts[str(seed)] = layout
        for group in GROUPS:
            config = factors(seed, group)
            config['bodies'] = layout['bodies'] if config['layout_enabled'] else {}
            config['geometry_accepted'] = layout['accepted'] if config['layout_enabled'] else True
            config['compiled_check'] = compiled_check(config, geometry)
            configs[str(seed)+'_'+group] = config
    return layouts, configs


def identities():
    from cm_common import verify as verify_motion
    previous = verify_motion()
    paths = set(previous['identities'])
    paths.update(str(p) for p in ROOT.glob('*.py'))
    paths.update(str(p) for p in ROOT.glob('*.sh'))
    paths.update(str(p) for p in ROOT.glob('*.sbatch'))
    paths.update(project_modules())
    return {p: sha(p) for p in sorted(paths)}


def project_modules():
    names = [getattr(module, '__file__', '') or '' for module in tuple(sys.modules.values())]
    return [name for name in names if name.startswith(str(ROOT.parent))
            and name.endswith('.py') and '/env_sim/' not in name and '/qwen35/' not in name]


def main():
    assert not (ROOT/'manifest.json').exists(), 'Preserve frozen protocol'
    suite = unittest.defaultTestLoader.discover(str(ROOT), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    scanned = unused()
    geometry = inventory()
    layouts, configs = build(geometry)
    value = dict(seeds=list(SEEDS), items=items(), geometry=geometry, layouts=layouts,
                 configs=configs, identities=identities(), test_used=False,
                 training_approved=False, model_calls=0, stage='qualification',
                 engineering_predecessor=dict(path=str(ROOT.parent/'scene_diversity_v1'),
                     manifest_sha256=sha(ROOT.parent/'scene_diversity_v1'/'manifest.json'),
                     reason='depth_segmentation_edge_audit', physical_executions=0))
    save(ROOT/'manifest.json', value)
    save(ROOT/'preflight.json', dict(passed=True, tests=result.testsRun,
         seeds_scanned_files=scanned, layouts=len(layouts), configs=len(configs),
         geometric_rejections=sum(not v['accepted'] for v in layouts.values()),
         manifest_sha256=sha(ROOT/'manifest.json')))
    print('FROZEN', len(configs), 'configs', flush=True)


if __name__ == '__main__':
    main()

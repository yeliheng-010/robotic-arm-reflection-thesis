"""来源、测试、未用种子和新布局全部冻结后才允许物理实验。"""
from pathlib import Path
import unittest
from cd_common import verify as verify_diagnostic
from cl_design import sampled_layout
from cl_geometry import verify_compiled
from pilot import extract_seeds
from cm_common import ROOT, DIAGNOSTIC, LAYOUT, PARENT, SEEDS, read, save, sha, validation_items


def unused_seeds():
    paths = set(PARENT.glob('*/manifest.json')) | set(PARENT.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not set(SEEDS)&used, 'New validation seed overlap'
    return paths


def validation_plan(geometry):
    layouts = {}
    for seed in SEEDS:
        layouts[str(seed)] = sampled_layout(seed,geometry)
        save(ROOT/'sampling_progress.json',layouts)
        assert layouts[str(seed)]['accepted'], 'Registered layout cannot be sampled'
    items = validation_items()
    for item in items:
        assert verify_compiled(item,layouts[str(item['seed'])],geometry)['checks']['passed']
    return dict(items=items,layouts=layouts,geometry=geometry)


def tests():
    from check_structure import main as structure
    structure()
    suite = unittest.defaultTestLoader.discover(str(ROOT),pattern='test_motion.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful() and result.testsRun==7
    from static_probe import main as probe
    probe()
    return result.testsRun


def freeze():
    assert not (ROOT/'manifest.json').exists()
    source = verify_diagnostic()
    previous = read(DIAGNOSTIC/'verification.json')
    assert previous['passed'] and previous['complete'] and previous['accounted']==73
    tested = tests()
    sources = unused_seeds()
    old_plan = read(LAYOUT/'plan.json')
    plan = validation_plan(old_plan['geometry'])
    files = set(ROOT.glob('*.py'))|set(ROOT.glob('*.sbatch'))|set(ROOT.glob('*.sh'))|{ROOT/'PROTOCOL.md',ROOT/'STATIC_PROBE.json'}
    files.update(sources)
    files.update(DIAGNOSTIC/name for name in ('manifest.json','verification.json'))
    identities = dict(source['identities'])
    identities.update({str(p):sha(p) for p in files})
    value = dict(identities=identities,cases=source['cases'],development_plan=old_plan,
        validation_plan=plan,seeds=list(SEEDS),test_used=False,training_approved=False,
        development_physical=22,validation_conditions=80,validation_trajectories=160)
    save(ROOT/'manifest.json',value)
    save(ROOT/'preflight.json',dict(passed=True,tests=tested,source_cases=11,new_seeds=40,
        new_conditions=80,compiled_checks=80,manifest_sha256=sha(ROOT/'manifest.json')))
    print('PASS: 11 development cases, 40 unused seeds, 80 validation conditions',flush=True)


if __name__=='__main__':
    freeze()

"""冻结局部执行协议和全部继承输入；不覆盖已冻结清单。"""
import unittest
from sd_common import read, save, sha
from route_inputs import ROOT, PREVIOUS, inputs


def verify():
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    return manifest


def main():
    assert not (ROOT/'manifest.json').exists(), 'Already frozen'
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    cases = inputs()
    identities = dict(read(PREVIOUS/'manifest.json')['identities'])
    files = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md',
             PREVIOUS/'manifest.json', PREVIOUS/'verification.json']
    for case in cases:
        files += [case['first']['result_path']]
        if not case['reused_success']:
            files += [ROOT/('preflight_'+case['id']+'.json')]
    identities.update({str(p): sha(p) for p in files})
    for path, digest in identities.items():
        assert sha(path) == digest, path
    save(ROOT/'manifest.json', dict(cases=cases, identities=identities,
         max_attempts=3, max_new_per_task=2, static_samples_per_segment=51,
         destination_clearance_m=.01, lifts_m=[.35,.45,.55], model_calls=0,
         scenes=['baseline','varied_noisy'], promotion_allowed=False,
         training_approved=False, development_seeds=True, tests=tests.testsRun))
    print('Frozen', sha(ROOT/'manifest.json'), flush=True)


if __name__ == '__main__':
    main()

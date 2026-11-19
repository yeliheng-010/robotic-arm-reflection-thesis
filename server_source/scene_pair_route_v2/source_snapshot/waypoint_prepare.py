"""静态有路才登记第三次尝试；冻结源代码、输入和预检结果。"""
import unittest
from sd_common import read, save, sha
from waypoint_inputs import ROOT, PREVIOUS, inputs


def verify():
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    return manifest


def main():
    assert not (ROOT/'manifest.json').exists()
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    cases = inputs()
    preflight = read(ROOT/'preflight.json')
    assert preflight['passed']
    selected = [r['id'] for r in preflight['rows'] if r['selected'] is not None]
    identities = dict(read(PREVIOUS/'manifest.json')['identities'])
    files = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md',
             *ROOT.glob('preflight*.json'), PREVIOUS/'manifest.json', PREVIOUS/'verification.json']
    for case in cases:
        files += [step['result_path'] for step in case['steps']]
        if 'prior_trace' in case:
            files.append(case['prior_trace'])
    identities.update({str(p):sha(p) for p in files})
    for path, digest in identities.items():
        assert sha(path) == digest, path
    save(ROOT/'manifest.json', dict(cases=cases, selected=selected, identities=identities,
         tests=tests.testsRun, max_attempts=3, shared_first_two=True, max_new_per_task=1,
         promotion_allowed=False, training_approved=False, model_calls=0))
    print('Frozen', sha(ROOT/'manifest.json'), 'selected', selected, flush=True)


if __name__ == '__main__':
    main()

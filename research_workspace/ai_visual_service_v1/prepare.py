import os
import unittest
from pathlib import Path
from f_common import read, save, sha
from vs_common import ROOT, CONDITIONS


def public(value):
    forbidden = {'root_cause', 'error_type', 'grasp_residual_xy', 'contact_details',
        'source_center', 'source_half', 'bin_center', 'qualification', 'successor', 'verified_recovery'}
    if isinstance(value, dict):
        assert not forbidden.intersection(value)
        for child in value.values():
            public(child)
    elif isinstance(value, list):
        for child in value:
            public(child)


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    source = ROOT.parent/'qualified_data_review_v1/inventory.json'
    inventory = read(source)
    assert all(sha(p) == h for p, h in inventory['identities'].items())
    identities = {str(source): sha(source)}
    inputs = []
    for name in CONDITIONS:
        row = next(r for r in inventory['rows'] if r['condition'] == name)
        assert row['eligible_natural'] and sha(row['input_path']) == row['input_sha256']
        bundle = read(row['input_path'])
        assert bundle['request']['after_attempt'] == 1
        public(bundle['request'])
        assert bundle['direct_messages'][1] == bundle['diagnostic_messages'][1]
        identities[row['input_path']] = row['input_sha256']
        identities.update(dict(zip(bundle['visual']['paths'], bundle['visual']['sha256'])))
        inputs.append(dict(condition=name, path=row['input_path']))
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md')]
    files += [ROOT.parent/'ai_visual_input_v1/mm_generator.py', ROOT.parent/'ai_diagnosis_failure_v1/f_generator.py']
    identities.update({str(p): sha(p) for p in files})
    save(ROOT/'manifest.json', dict(inputs=inputs, identities=identities, max_calls=4,
        image_roots=[str(ROOT.parent/'natural_qualified_pilot_v1/cases')], tests=tested.testsRun,
        physical_attempts=0, training_ready=False, causal_correctness_not_established=True))
    print(dict(tests=tested.testsRun, max_model_calls=4), flush=True)


if __name__ == '__main__':
    main()

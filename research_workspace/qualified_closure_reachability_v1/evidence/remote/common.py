from pathlib import Path
from qualified_prompt_checkpoint_v1.protocol import read, save, sha

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
PARENT = PROJECT / 'qualified_checkpoint_preflight_v1'
CODE = PROJECT / 'improvement_20261019/code'


def verify():
    manifest = read(RUN / 'manifest.json')
    assert manifest['max_model_calls'] == manifest['max_physical_attempts'] == manifest['max_training_runs'] == 0
    assert manifest['fixed_configurations'] == 5 and manifest['max_diagnostic_runs'] == 1
    for name, expected in manifest['identities'].items():
        assert sha(name) == expected, name
    return manifest

"""同一条件修订验证：旧失败和本轮预算分别登记。"""
from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
TRIAL = PARENT/'trial_gpu_v3'


def prepare():
    assert not TRIAL.exists()
    previous = verify(PARENT/'trial_gpu_v2/manifest.json')
    reviewed = verify(PARENT/'physical_fix_v1/review.json')
    partial = verify(PARENT/'physical_fix_v1/partial_audit.json')
    assert partial['physical_attempts_consumed'] == 1
    assert partial['status'] == 'partial_execution_software_failure'
    assert read(PARENT/'trial_gpu_v2/cases/964345/first/lifecycle.json')['released']
    identities = dict(previous['identities'], **reviewed['identities'], **partial['identities'])
    paths = list(ROOT.glob('*.py')) + list(ROOT.glob('*.sbatch')) + list(ROOT.glob('*.sh'))
    paths += [PARENT/'physical_fix_v1/review.json', PARENT/'physical_fix_v1/partial_audit.json']
    identities.update({str(p): sha(p) for p in paths})
    row = previous['entry']
    save(TRIAL/'manifest.json', dict(entry=row, cases=[row['case']], identities=identities,
        max_attempts=1, model_calls=0, training_updates=0,
        algorithm='oriented_transfer_explicit_planning_scope',
        previous_consumed_trial=str(PARENT/'trial_gpu_v2'),
        independent_new_condition=False, authorization='User accepted independent revised physical validation'))
    save(TRIAL/'qualification/964345/result.json', dict(qualified=True,
        manifest_sha256=sha(TRIAL/'manifest.json'),
        geometry=read(PARENT/'trial_gpu_v2/qualification/964345/result.json')['geometry']))


def execution():
    prior = verify(TRIAL/'manifest.json')
    assert read(TRIAL/'preflight_result.json')['passed']
    assert not (TRIAL/'cases').exists()
    paths = [TRIAL/'manifest.json', TRIAL/'preflight_result.json']
    identities = dict(prior['identities'])
    identities.update({str(p): sha(p) for p in paths})
    save(TRIAL/'execution_manifest.json', dict(identities=identities, max_physical_attempts=1,
        same_condition_revision=True, model_calls=0, training_updates=0))

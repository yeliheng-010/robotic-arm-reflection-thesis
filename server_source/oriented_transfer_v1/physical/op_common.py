from pathlib import Path
from cc_common import read,save,sha,verify

ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
TRIAL=PARENT/'trial_gpu'
STATIC=PARENT/'path_v2/results'


def entry():
    return verify(TRIAL/'manifest.json')['entry']


def prepare():
    assert not TRIAL.exists()
    previous=verify(STATIC/'manifest.json')
    row=previous['rows'][0]
    audit=verify(STATIC/'audit'/row['name']/'result.json')
    assert audit['passed'] and audit['qualified'] and audit['independent']
    identities=dict(previous['identities'],**audit['identities'])
    paths=[STATIC/'manifest.json',STATIC/'audit'/row['name']/'result.json',
        *ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'manifest.json',dict(entry=row,cases=[row['case']],identities=identities,
        max_attempts=1,model_calls=0,training_updates=0,algorithm='oriented_tilt_held_joint_path',
        scope='Frozen-input controlled physical validation, not general collection entry'))
    save(TRIAL/'qualification'/str(row['case']['item']['seed'])/'result.json',dict(qualified=True,
        manifest_sha256=sha(TRIAL/'manifest.json'),geometry=dict(passed=True,status='selected',
        source=str(STATIC/'audit'/row['name']/'result.json'))))

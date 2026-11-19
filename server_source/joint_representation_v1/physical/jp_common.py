"""一次物理尝试前冻结实际入口及已复算规划。"""
from pathlib import Path
from js_common import SOURCE, inputs, read, save, sha, verify
from jr_probe import ROOT as PARENT, RUN

ROOT = Path(__file__).resolve().parent
TRIAL = PARENT/'trial'


def registered():
    return verify(TRIAL/'manifest.json')['cases'][0]


def prepare():
    assert not TRIAL.exists()
    previous = verify(RUN/'manifest.json')
    audit = verify(PARENT/'audit/result.json')
    assert audit['passed'] and audit['qualified'] and audit['independent']
    case,_ = inputs()
    identities = dict(previous['identities'],**audit['identities'])
    paths = [PARENT/'audit/result.json',RUN/'result.json',*ROOT.glob('*.py'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'manifest.json',dict(cases=[case],identities=identities,max_attempts=1,
        max_model_calls=0,training_updates=0,algorithm='equivalent_joint_angles'))
    save(TRIAL/'qualification'/str(case['item']['seed'])/'result.json',dict(qualified=True,
        manifest_sha256=sha(TRIAL/'manifest.json'),geometry=dict(passed=True,status='selected',
        source=str(PARENT/'audit/result.json'),source_sha256=sha(PARENT/'audit/result.json'))))

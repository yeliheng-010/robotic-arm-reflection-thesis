"""保持已冻结执行逻辑，只在与原观测一致的GPU资源下重新做门禁。"""
import sys
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import jp_common
import jp_worker
import jp_audit
from jp_common import PARENT, read, save, sha, verify

ROOT = Path(__file__).resolve().parent
TRIAL = PARENT/'trial_gpu'


def prepare():
    assert not TRIAL.exists()
    prior = verify(PARENT/'trial/manifest.json')
    lifecycle = read(PARENT/'trial/preflight/lifecycle.json')
    assert lifecycle['released'] and lifecycle['exit_exception']=='PlanMismatch'
    assert read(PARENT/'trial/preflight/bridge.json')['planners'] == []
    paths = [PARENT/'trial/manifest.json',*ROOT.glob('*.py'),*ROOT.glob('*.sbatch')]
    identities = dict(prior['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'manifest.json',dict(cases=prior['cases'],identities=identities,max_attempts=1,
        max_model_calls=0,training_updates=0,algorithm='equivalent_joint_angles',
        change='GPU allocation restored to match original sensing job; prior trial had zero task motion'))
    seed = str(prior['cases'][0]['item']['seed'])
    qualification = read(PARENT/'trial/qualification'/seed/'result.json')
    qualification['manifest_sha256'] = sha(TRIAL/'manifest.json')
    save(TRIAL/'qualification'/seed/'result.json',qualification)


if __name__ == '__main__':
    mode = sys.argv[1]
    with patch.object(jp_common,'TRIAL',TRIAL),patch.object(jp_worker,'TRIAL',TRIAL), \
         patch.object(jp_audit,'TRIAL',TRIAL):
        {'prepare':prepare,'preflight':jp_worker.preflight,'execute':jp_worker.execute,
         'audit':jp_audit.main}[mode]()

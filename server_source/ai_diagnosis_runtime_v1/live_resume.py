"""冻结兼容修订；只执行尚未启动的增强条件，严格禁止重跑原配置。"""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read, save, sha
from live_run import verify
import live_session
from live_requests_v2 import build
from recover_baseline import recover

ROOT = Path(__file__).resolve().parent
REVISION_FILES = ('live_requests_v2.py', 'test_revision.py', 'recover_baseline.py', 'live_resume.py',
                  'resume.sbatch', 'audit_live.py', 'audit_motion_live.py', 'audit_sensor_live.py', 'audit.sbatch')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    assert not (ROOT/'revision_manifest.json').exists()
    suite = unittest.TestLoader().discover(str(ROOT), pattern='test_revision.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    baseline, varied = manifest['cases']
    assert baseline['item']['group'] == 'baseline' and varied['item']['group'] == 'varied_noisy'
    assert not (ROOT/'runs'/varied['item']['id']).exists()
    assert read(ROOT/'runs'/baseline['item']['id']/'execution/result.json')['success']
    paths = [ROOT/name for name in REVISION_FILES]
    paths += [p for p in (ROOT/'runs').rglob('*') if p.is_file()]
    save(ROOT/'revision_manifest.json', dict(parent_sha256=sha(ROOT/'manifest.json'),
         identities={str(p): sha(p) for p in paths}, reused=baseline['item']['id'],
         remaining_execution=varied['item']['id'], max_additional_attempts=1,
         reason='Normalize tuple at request boundary; no motion or sensor changes'))
    rows = [recover(baseline, ROOT)]
    with patch.object(live_session, 'build', build):
        rows.append(live_session.run_once(varied, ROOT/'runs'/varied['item']['id']))
    verify()
    revision = read(ROOT/'revision_manifest.json')
    assert all(sha(p) == h for p, h in revision['identities'].items())
    save(ROOT/'run_complete.json', dict(rows=rows, actual_new_attempts=2, model_calls=0, training_runs=0,
         manifest_sha256=sha(ROOT/'manifest.json'), revision_sha256=sha(ROOT/'revision_manifest.json')))
    print(rows, flush=True)


if __name__ == '__main__':
    main()

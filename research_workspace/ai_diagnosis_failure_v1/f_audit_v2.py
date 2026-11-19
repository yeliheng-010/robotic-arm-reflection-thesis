"""冻结审计修订，保留原RGB严格相等失败，不重跑任何物理过程。"""
import os
import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from f_common import ROOT, read, save, sha, verify
from coverage_gate import evaluate
from f_sensor_v2 import audit as sensor_audit
import f_audit

FILES = ('f_sensor_v2.py', 'test_f_sensor_v2.py', 'f_audit_v2.py', 'audit_v2.sbatch',
         'f_rgb_diagnostic.py', 'rgb.sbatch', 'rgb_diagnostic.json', 'audit-5886.log')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    tests = unittest.TestLoader().discover(str(ROOT), pattern='test_f_sensor_v2.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    assert result.wasSuccessful()
    paths = [ROOT/name for name in FILES]+[p for p in (ROOT/'run').rglob('*') if p.is_file()]
    save(ROOT/'audit_revision_manifest.json', dict(parent_sha256=sha(ROOT/'manifest.json'),
         reason='RGB artifacts vary by one level; exact state and depth remain required; RGB not input to text policy',
         tests=result.testsRun, physical_executions=0, identities={str(p): sha(p) for p in paths}))
    assert read(ROOT/'run_complete.json')['attempts'] == 1
    with patch.object(f_audit, 'audit_sensor', sensor_audit):
        row = f_audit.inspect(manifest['case'])
    coverage = evaluate([row])
    assert coverage['model_smoke_gate']
    revision = read(ROOT/'audit_revision_manifest.json')
    assert all(sha(p) == h for p, h in revision['identities'].items())
    verify()
    value = dict(passed=True, model_smoke_gate=True, row=row, coverage=coverage,
         actual_new_attempts=1, natural_failure_samples=0, model_calls=0, training_runs=0,
         manifest_sha256=sha(ROOT/'manifest.json'), audit_revision_sha256=sha(ROOT/'audit_revision_manifest.json'),
         identities={str(p): sha(p) for p in paths})
    save(ROOT/'verification.json', value)
    print({k: v for k, v in value.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()

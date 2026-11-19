"""新增审计修订，不修改冻结源码、manifest或物理记录。"""
import os
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import save, sha
from goal_inputs import ROOT
import goal_audit as original
from goal_audit_geometry_v2 import audit
from geometry_consistency import REBUILD_ATOL_M

REVISION_FILES = ('geometry_consistency.py', 'test_geometry_consistency.py',
                  'goal_audit_geometry_v2.py', 'goal_audit_v2.py', 'audit_v2.sbatch',
                  'geometry_diagnostic.py', 'geometry_diagnostic.sbatch',
                  'geometry_diagnostic.json')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    output = ROOT/'verification_v2.json'
    supplement = ROOT/'audit_revision_manifest.json'
    assert not output.exists() and not supplement.exists()
    identities = {name: sha(ROOT/name) for name in REVISION_FILES}
    metadata = dict(audit_revision=2, reconstruction_atol_m=REBUILD_ATOL_M,
                    original_manifest_sha256=sha(ROOT/'manifest.json'), identities=identities,
                    slurm_job_id=os.environ['SLURM_JOB_ID'], original_failed_job='5840',
                    diagnostic_job='5849', physical_attempts_added_by_revision=0)
    captured = {}

    def capture(path, result):
        assert path == ROOT/'verification.json'
        captured.update(result)

    with patch.object(original, 'audit_geometry', audit), patch.object(original, 'save', capture):
        original.main()
    assert captured['passed']
    assert identities == {name: sha(ROOT/name) for name in REVISION_FILES}
    save(supplement, metadata)
    save(output, dict(captured, audit_revision=2, audit_revision_sha256=sha(supplement)))
    print('Revision 2 audit saved; frozen sources and physical records unchanged', flush=True)


if __name__ == '__main__':
    main()

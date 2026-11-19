"""隔离可辨识的重建不一致，其他异常仍阻断采集。"""
import os
import sys
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import PHYSICS, save, sha, verify

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'recovery_integrity_v2'
sys.path.insert(0, str(BASE))
import ig_audit
import geometry_v3
from iv3_geometry import strict_compare, ReconstructionMismatch


def inspect(case):
    with patch.object(geometry_v3, 'compare', strict_compare):
        return ig_audit.inspect(case)


def evaluate(case):
    folder, result, _ = ig_audit.case_steps(case)
    _, contacts = ig_audit.contact_evidence(case)
    reason, evidence = None, {}
    if any(r['self_contact_samples'] for r in contacts):
        reason = 'measured_robot_self_contact'
    else:
        try:
            evidence['row'] = inspect(case)
        except ReconstructionMismatch as error:
            reason = 'dynamic_geometry_reconstruction_mismatch'
            evidence['reconstruction'] = error.evidence
    value = dict(id=case['item']['id'], passed=reason is None,
        manifest_sha256=sha(PHYSICS / 'manifest.json'), audit_version=3, **evidence)
    if reason:
        value.update(reason=reason, contacts=contacts, consumed_attempts=result['attempts'],
            excluded_entire_condition=True, eligible_natural_snapshots=0, verified_recoveries=0,
            full_safety_audit_completed=False)
    files = [p for p in folder.rglob('*') if p.is_file()]
    files += [ROOT / 'source_manifest.json', BASE / 'source_manifest.json']
    value['identities'] = {str(p): sha(p) for p in files}
    return value


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(ROOT / 'source_manifest.json')
    verify(BASE / 'source_manifest.json')
    name = sys.argv[1]
    case = next(c for c in verify(PHYSICS / 'manifest.json')['cases'] if c['item']['id'] == name)
    value = evaluate(case)
    accepted = PHYSICS / 'audits' / (name+'.json')
    rejected = PHYSICS / 'audit_rejections' / (name+'.json')
    assert not accepted.exists() and not rejected.exists()
    save(accepted if value['passed'] else rejected, value)
    print(dict(id=name, passed=value['passed'], reason=value.get('reason')), flush=True)


if __name__ == '__main__':
    main()

"""兼容原安全拒绝和新增完整性拒绝，仍要求每条件唯一去向。"""
from unittest.mock import patch
from iv3_audit import ROOT, BASE
from collection_common import PHYSICS, read, sha, verify
import ig_merge

REASONS = {'measured_robot_self_contact', 'dynamic_geometry_reconstruction_mismatch'}


def disposition(case):
    name = case['item']['id']
    accepted = PHYSICS / 'audits' / (name+'.json')
    rejected = PHYSICS / 'audit_rejections' / (name+'.json')
    assert accepted.exists() != rejected.exists(), name
    path = accepted if accepted.exists() else rejected
    value = verify(path)
    assert value['passed'] is accepted.exists()
    assert value['manifest_sha256'] == sha(PHYSICS / 'manifest.json')
    result = read(PHYSICS / 'cases' / name / 'result.json')
    assert result['status'] == 'completed' and 1 <= result['attempts'] <= 7
    if accepted.exists():
        assert value['row']['attempts'] == result['attempts']
    else:
        assert value['reason'] in REASONS
        assert value['consumed_attempts'] == result['attempts']
        assert value['excluded_entire_condition']
        assert value['eligible_natural_snapshots'] == value['verified_recoveries'] == 0
    return dict(id=name, accepted=accepted.exists(), attempts=result['attempts'], path=str(path))


def main():
    verify(BASE / 'source_manifest.json')
    with patch.object(ig_merge, 'ROOT', ROOT), patch.object(ig_merge, 'disposition', disposition):
        ig_merge.main()


if __name__ == '__main__':
    main()

"""只接纳完整安全审计，真实自接触单列且保留原文件。"""
import os
import sys
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import collect_audit
import rb_audit
import sv_requests_v2
import sv_audit_replay
import sv_strategy_audit
from audit_v5 import audit_attempt
from sv_strategy_requests import build
from sr_audit import measured
from collection_common import PHYSICS, BRANCHES, read, save, sha, verify
from ig_policy import audit_disposition
import geometry_v3

ROOT = Path(__file__).resolve().parent


def case_steps(case):
    folder = PHYSICS / 'cases' / case['item']['id']
    result = read(folder / 'result.json')
    assert result['status'] == 'completed' and result['manifest_sha256'] == sha(PHYSICS / 'manifest.json')
    assert set(result['methods']) == set(BRANCHES)
    steps = {}
    for branch in BRANCHES:
        for step in read(folder / branch / 'result.json')['ledger']['steps']:
            assert steps.setdefault(step['session_path'], step) == step
    assert len(steps) == result['attempts'] <= 7
    return folder, result, steps


def contact_evidence(case):
    _, result, steps = case_steps(case)
    rows = []
    for path in steps:
        contact = measured(Path(path))
        contact.pop('closing_end')
        rows.append(dict(path=path, **contact))
    return result, rows


def inspect(case):
    with patch.object(sv_requests_v2, 'ROOT', PHYSICS), \
         patch.object(sv_audit_replay, 'build', build), \
         patch.object(sv_strategy_audit, 'audit_attempt', audit_attempt), \
         patch.object(rb_audit, 'geometry', geometry_v3.audit):
        return collect_audit.inspect(case)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(ROOT / 'source_manifest.json')
    name = sys.argv[1]
    case = next(c for c in verify(PHYSICS / 'manifest.json')['cases'] if c['item']['id'] == name)
    folder, _, _ = case_steps(case)
    result, contacts = contact_evidence(case)
    decision = audit_disposition([r['self_contact_samples'] for r in contacts])
    files = [p for p in folder.rglob('*') if p.is_file()] + [ROOT / 'source_manifest.json']
    value = dict(id=name, manifest_sha256=sha(PHYSICS / 'manifest.json'),
        identities={str(p): sha(p) for p in files})
    if decision == 'quarantine':
        value.update(passed=False, reason='measured_robot_self_contact', contacts=contacts,
            consumed_attempts=result['attempts'], excluded_entire_condition=True,
            eligible_natural_snapshots=0, verified_recoveries=0)
        output = PHYSICS / 'audit_rejections' / (name+'.json')
    else:
        value.update(passed=True, row=inspect(case), audit_version=2)
        output = PHYSICS / 'audits' / (name+'.json')
    assert not output.exists()
    save(output, value)
    print(dict(id=name, disposition=decision, attempts=result['attempts']), flush=True)


if __name__ == '__main__':
    main()

"""独立核对输入、保护后果和旧成功回归；失败不改称成功。"""
import os
import json
import numpy as np
from unittest.mock import patch
from sd_common import read, save, sha
from guard_prepare import ROOT, DIAGNOSTIC, shadow
from guard_worker import same_input
from guard_policy import forbidden, release_reason
from guard_runtime import context, contact_checker
import reflection.monitors as monitors
import stability.prepose as prepose
import cm_geometry


def trace(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def aliases():
    modules = (monitors, prepose, cm_geometry)
    originals = [m.robot_environment_contacts for m in modules]
    with context(dict(source='RedBlock'), {}):
        assert len({id(m.robot_environment_contacts) for m in modules}) == 1
        assert all(m.robot_environment_contacts is not old for m, old in zip(modules, originals))
    assert all(m.robot_environment_contacts is old for m, old in zip(modules, originals))
    contact = dict(roots=['ur5e_base', 'BlueBin'], geoms=['arm', 'wall'])
    with patch('guard_runtime.contact_rows', return_value=[contact]):
        assert contact_checker('RedBlock')(None, None, ignore=('RedBlock', 'BlueBin')) == [('ur5e_base', 'BlueBin')]


def audit_case(case):
    folder = ROOT/'physics'/case['id']
    evidence = read(folder/'audit.json')
    assert sha(evidence['step']['result_path']) == evidence['step']['result_sha256']
    assert sha(folder/'contacts.jsonl') == evidence['trace_sha256']
    assert sha(folder/'guard.json') == evidence['guard_sha256']
    before, after = same_input(case, evidence['step'])
    rows, gate = trace(folder/'contacts.jsonl'), read(folder/'guard.json')
    if gate['release_checked']:
        assert gate['reason'] == release_reason(gate['release'])
        assert gate['open_called'] == (gate['reason'] is None)
    if after['physical_success']:
        assert gate['release_checked'] and gate['open_called'] and gate['reason'] is None
    hits = [r for r in rows if any(forbidden(c, case['item']['source']) for c in r['contacts'])]
    error = (after['error'] or {}).get('error_type')
    unchanged_success = False
    if before['physical_success'] and after['physical_success']:
        for key in ('position', 'placement_residual_xy', 'xy_error_m', 'tilt_deg'):
            np.testing.assert_array_equal(before['evaluation'][key], after['evaluation'][key])
        unchanged_success = True
    return dict(id=case['id'], old_success=before['physical_success'], success=after['physical_success'],
                unchanged_success=unchanged_success, error=error, gate=gate,
                stop_time=rows[-1]['time'], forbidden_contact_samples=len(hits),
                final_contacts=rows[-1]['contacts'], result_sha256=evidence['step']['result_sha256'])


def release_only():
    original = trace(DIAGNOSTIC/'physics'/'961104_varied_noisy_0'/'contacts.jsonl')
    current = trace(ROOT/'physics'/'961104_release_only'/'contacts.jsonl')
    prefix = lambda rows: [r for r in rows if r['action'] in ('move_to_grasp_pose', 'close_gripper', 'move_to_point')]
    assert prefix(original) == prefix(current)
    gate = read(ROOT/'physics'/'961104_release_only'/'guard.json')
    assert gate['reason'] == 'object_dropped' and not gate['open_called']
    np.testing.assert_array_equal(current[-1]['ctrl'], next(r['ctrl'] for r in original
        if r['action'] == 'open_gripper' and r['event'] == 'begin'))
    return dict(identical_prefix=True, no_open_command=True)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = read(ROOT/'manifest.json')
    assert read(ROOT/'preflight.json')['manifest_sha256'] == sha(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    assert read(ROOT/'shadow.json') == shadow()
    aliases()
    rows = [audit_case(case) for case in manifest['cases']]
    result = dict(passed=True, attempts=len(rows), rows=rows, release_only=release_only(),
                  preserved_successes=sum(r['unchanged_success'] for r in rows),
                  regressions=sum(r['old_success'] and not r['success'] for r in rows),
                  promotion_allowed=False, manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'verification.json', result)
    print({k: v for k, v in result.items() if k != 'rows'}, flush=True)


if __name__ == '__main__':
    main()

"""最终范围修订的共享账本及真实门控证据审计。"""
import os
import math
from unittest.mock import patch
import numpy as np
from sd_common import read, save, sha
import guard_audit
import guard_runtime
import reflection.monitors as monitors
import stability.prepose as prepose
import cm_geometry
from guard_scope import context
from contact_policy import forbidden
from scope_run import ROOT, PREVIOUS, scan


def integration():
    contacts = [dict(roots=['2f85_base', 'RedBlock'], geoms=['spring', 'block']),
                dict(roots=['ur5e_base', 'BlueBin'], geoms=['arm', 'wall'])]
    modules = (monitors, prepose, cm_geometry)
    original = [m.robot_environment_contacts for m in modules]
    with context(dict(source='RedBlock'), {}), patch.object(guard_runtime, 'contact_rows', return_value=contacts):
        for module in modules:
            assert module.robot_environment_contacts(None, None, ignore=('RedBlock', 'BlueBin')) == [('ur5e_base', 'BlueBin')]
    assert all(m.robot_environment_contacts is f for m, f in zip(modules, original))


def release_snapshot(case, folder):
    gate = read(folder/'guard.json')
    if not gate['release_checked']:
        return
    rows = guard_audit.trace(folder/'contacts.jsonl')
    row = next(r for r in rows if r['time'] == gate['release']['time'])
    np.testing.assert_array_equal([row['tcp'][i][3] for i in range(3)], gate['release']['actual'])
    assert gate['release']['held'] == all(case['item']['source'] in row['pads'][s] for s in ('left', 'right'))
    evidence = read(folder/'audit.json')
    record = read(evidence['step']['result_path'])['records'][0]
    target = np.array(record['execution_adapter']['planned_poses'][-1])[:3, 3]
    np.testing.assert_allclose(target, gate['release']['expected'], atol=1e-12, rtol=0)
    assert math.isclose(gate['release']['xy_error_m'],
        math.dist(gate['release']['actual'][:2], gate['release']['expected'][:2]), abs_tol=1e-12)


def inspect_case(case, selected):
    reused = case['id'] not in selected
    root = PREVIOUS if reused else ROOT
    folder = root/'physics'/case['id']
    with patch.object(guard_audit, 'ROOT', root), patch.object(guard_audit, 'forbidden', forbidden):
        result = guard_audit.audit_case(case)
    release_snapshot(case, folder)
    current = read(read(folder/'audit.json')['step']['result_path'])['records'][0]
    reference = read(read(PREVIOUS/'physics'/case['id']/'audit.json')['step']['result_path'])['records'][0]
    assert current['approach_plan'] == reference['approach_plan']
    if case['id'] == '961103_varied_noisy_0':
        assert result['error'] == 'collision' and not result['gate']['open_called']
        assert any('ur5e_base' in c['roots'] and case['item']['destination'] in c['roots']
                   for c in result['final_contacts'])
    result.update(reused=reused, evidence_root=str(folder))
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    assert manifest['scans'] == [scan(c) for c in manifest['cases']]
    assert all(c['step']['index'] == 1 for c in manifest['cases'])
    integration()
    results = [inspect_case(c, manifest['selected']) for c in manifest['cases']]
    with patch.object(guard_audit, 'ROOT', PREVIOUS):
        release = guard_audit.release_only()
    output = dict(passed=True, accounted=10, actual_new_attempts=2, reused_cases=8,
        total_new_attempts_this_round=12, preserved_successes=sum(r['unchanged_success'] for r in results),
        gains=sum(not r['old_success'] and r['success'] for r in results),
        regressions=sum(r['old_success'] and not r['success'] for r in results), rows=results,
        release_only=release, promotion_allowed=False, full_48_conditions_rerun=False,
        manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'verification.json', output)
    print({k: v for k, v in output.items() if k != 'rows'}, flush=True)


if __name__ == '__main__':
    main()

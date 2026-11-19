"""全量物理记账、重放及篡改拒绝后才能通过门禁。"""
import sys
from copy import deepcopy
from cd_common import ROOT, SHARDS, verify, read, save, sha, gate
from cd_physics_audit import audit_result
from physics_run import indices
from report import write


def reject(result, branch, manifest, *, mutate):
    value = deepcopy(result)
    mutate(value)
    try:
        audit_result(value,branch,manifest)
    except (AssertionError,ValueError,KeyError):
        return
    raise AssertionError('Tampering accepted')


def tamper(result, branch, manifest):
    reject(result,branch,manifest,mutate=lambda r:r['step'].update(success=not r['step']['success']))
    reject(result,branch,manifest,mutate=lambda r:r['step']['state']['parameters'].update(lift_height=.48))
    reject(result,branch,manifest,mutate=lambda r:r['step'].update(result_sha256='0'*64))
    reject(result,branch,manifest,mutate=lambda r:r.update(training_approved=True))
    reject(result,branch,manifest,mutate=lambda r:r.update(extra_observations=1))
    return 5


def stages(manifest, phase):
    phases = ['smoke'] if phase=='smoke' else ['smoke','batch']
    for name in phases:
        for shard in range(SHARDS):
            status = read(ROOT/'stages'/name/f'{shard}.json')
            expected = indices(manifest,name)[shard::SHARDS]
            assert status['status']=='completed' and status['indices']==expected
            assert status['completed']==status['expected']==len(expected)


def audit_rows(manifest, selected):
    rows, expected_paths = [], set()
    for index in selected:
        branch = manifest['branches'][index]
        folder = ROOT/'tasks'/f'{index:03d}'
        result = read(folder/'result.json')
        checked = audit_result(result,branch,manifest)
        assert checked == read(folder/'summary.json')
        rows.append(checked)
        expected_paths.add(folder/'attempt_3/result.json')
    assert expected_paths == set((ROOT/'tasks').glob('*/attempt_*/result.json'))
    assert {f'{i:03d}' for i in selected} == {p.name for p in (ROOT/'tasks').iterdir()}
    return rows


def main(phase):
    manifest = verify()
    model = gate('gate_model.json')
    for path, digest in model['identities'].items():
        assert sha(path)==digest, 'Model labels changed after model gate'
    stages(manifest,phase)
    selected = manifest['smoke'] if phase=='smoke' else list(range(len(manifest['branches'])))
    rows = audit_rows(manifest,selected)
    first = manifest['branches'][selected[0]]
    tests = tamper(read(ROOT/'tasks'/f"{first['index']:03d}"/'result.json'),first,manifest)
    value = dict(passed=True,complete=phase=='final',accounted=len(rows),rows=rows,
        manifest_sha256=sha(ROOT/'manifest.json'),tamper_checks=tests,
        test_used=False,training_approved=False,task_calls=44,startup_calls=2)
    if phase=='final':
        assert sum(len(r['replays']) for r in rows)==22
        value['analysis'] = write(manifest,rows,model)
    save(ROOT/('gate_physics_smoke.json' if phase=='smoke' else 'verification.json'),value)
    print(f'PASS: {phase}, {len(rows)} physical branches',flush=True)


if __name__=='__main__':
    assert sys.argv[1] in ('smoke','final')
    main(sys.argv[1])

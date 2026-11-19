"""只继续未执行的第二种子；旧失败控制器与首阶段尝试保留。"""
import os
from rb_common import ROOT, SEEDS, read, save, sha, verify
from rb_controller import run, CASE_SECONDS, AUDIT_SECONDS
from nc_common import status


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    assert read(ROOT/f'audit_{SEEDS[0]}.json')['passed']
    assert not (ROOT/'complete.json').exists()
    names = ('rb_audit_v2.py', 'audit_v2.sbatch', 'rb_continue.py', 'continue.sbatch')
    identities = {str(ROOT/n): sha(ROOT/n) for n in names}
    save(ROOT/'continuation_manifest.json', dict(identities=identities, manifest_sha256=sha(ROOT/'manifest.json'),
        first_audit_sha256=sha(ROOT/f'audit_{SEEDS[0]}.json'), first_stage_rerun=False))
    for case in manifest['cases']:
        if case['item']['seed'] == SEEDS[1]:
            name = case['item']['id']
            assert not (ROOT/'cases'/name).exists()
            run('rb_worker.py', [name], name=name, timeout=CASE_SECONDS)
    run('rb_audit_v2.py', ['--seed', str(SEEDS[1])], name=f'audit_{SEEDS[1]}', timeout=AUDIT_SECONDS)
    rows = [r for seed in SEEDS for r in read(ROOT/f'audit_{seed}.json')['rows']]
    attempts = sum(r['attempts'] for r in rows)
    assert attempts <= manifest['max_attempts'] and all(sha(p) == h for p, h in identities.items())
    verify()
    save(ROOT/'complete.json', dict(passed=True, attempts=attempts, rows=rows, model_calls=0,
        training_ready=False, audit_entry_revision=2, first_stage_rerun=False))
    status(ROOT/'status.json', dict(stage='engineering_pilot_completed', attempts=attempts))


if __name__ == '__main__':
    main()

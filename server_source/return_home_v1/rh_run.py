"""只执行行为改变的条件，汇总时明确区分新执行与复用。"""
import os
import sys
import subprocess
from cc_common import read, save, sha, verify
from rh_prepare import ROOT, REPAIR, SOURCE

TIMEOUT_SECONDS = 900


def run(script, seed):
    path = REPAIR/'logs'/(script+'_'+str(seed)+'.log')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT/script), str(seed)],
            stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=TIMEOUT_SECONDS)


def main():
    manifest = verify(REPAIR/'manifest.json')
    save(REPAIR/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    for seed in manifest['changed_seeds']:
        run('rh_worker.py', seed)
        run('rh_audit.py', seed)
    rows = []
    for case in manifest['all_cases']:
        seed = case['item']['seed']
        reused = seed in manifest['reused_seeds']
        audit = verify((SOURCE if reused else REPAIR)/'audits'/(str(seed)+'.json'))
        rows.append(dict(seed=seed, reused=reused, audit_passed=audit['passed'],
            success=audit.get('new_success') if reused else audit.get('success')))
    verify(REPAIR/'manifest.json')
    save(REPAIR/'result.json', dict(complete=True, rows=rows,
        new_attempts=len(manifest['changed_seeds']), reused_conditions=len(manifest['reused_seeds']),
        successes=sum(r['audit_passed'] and r['success'] is True for r in rows),
        model_calls=0, training_updates=0, manifest_sha256=sha(REPAIR/'manifest.json')))
    print(rows, flush=True)


if __name__ == '__main__':
    main()

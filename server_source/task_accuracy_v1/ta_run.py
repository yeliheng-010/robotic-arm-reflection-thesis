"""逐一运行全部登记布局；任何异常停机留账，不静默重跑。"""
import os
import sys
import subprocess
from ta_common import ROOT, PILOT, SEEDS, read, save, sha, verify
from ta_protocol import summarize

TIMEOUT_SECONDS = 900


def run(script, seed):
    path = PILOT/'logs'/(script+'_'+str(seed)+'.log')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT/script), str(seed)],
            stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=TIMEOUT_SECONDS)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(PILOT/'manifest.json')
    save(PILOT/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    rows = []
    for seed in SEEDS:
        run('ta_worker.py', seed)
        run('ta_audit.py', seed)
        row = read(PILOT/'cases'/str(seed)/'result.json')
        audit = verify(PILOT/'audits'/(str(seed)+'.json'))
        row.update(audit_passed=audit['passed'], old_success=audit.get('old_success'))
        rows.append(row)
        save(PILOT/'rows'/(str(seed)+'.json'), row)
        print(row, flush=True)
    verify(PILOT/'manifest.json')
    save(PILOT/'result.json', dict(complete=True, rows=rows, counts=summarize(rows, SEEDS),
        model_calls=0, training_updates=0, eligible_for_training=False,
        manifest_sha256=sha(PILOT/'manifest.json')))


if __name__ == '__main__':
    main()

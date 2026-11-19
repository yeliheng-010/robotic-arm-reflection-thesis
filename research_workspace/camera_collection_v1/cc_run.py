"""资格、执行、独立审计逐项留账；不自动重跑已经消费的条件。"""
import os
import sys
import subprocess
from cc_common import ROOT, PILOT, read, save, sha, verify
from cc_policy import paired_counts

TIMEOUT_SECONDS = 900


def run(script, seed):
    path = PILOT/'logs'/(script+'_'+str(seed)+'.log')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT/script), str(seed)],
            stdout=stream, stderr=subprocess.STDOUT, timeout=TIMEOUT_SECONDS, check=True)


def process(case):
    seed = case['item']['seed']
    run('cc_qualify.py', seed)
    qualification = read(PILOT/'qualification'/str(seed)/'result.json')
    row = dict(seed=seed, qualified=qualification['qualified'], qualification_status=qualification['status'])
    if not row['qualified']:
        return row
    run('cc_worker.py', seed)
    row.update(read(PILOT/'cases'/str(seed)/'result.json'))
    run('cc_audit.py', seed)
    audit = verify(PILOT/'audits'/(str(seed)+'.json'))
    row['audit_passed'] = audit['passed']
    row['old_success'] = read(case['camera_collection']['old_step'])['success']
    return row


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify(PILOT/'manifest.json')
    save(PILOT/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    rows = []
    for case in manifest['cases']:
        row = process(case)
        rows.append(row)
        save(PILOT/'rows'/(str(row['seed'])+'.json'), row)
        print(row, flush=True)
    verify(PILOT/'manifest.json')
    save(PILOT/'result.json', dict(complete=True, rows=rows, counts=paired_counts(rows),
        registered_camera_layouts=9, camera_rejections=4, model_calls=0, training_updates=0,
        eligible_for_training=False, manifest_sha256=sha(PILOT/'manifest.json')))


if __name__ == '__main__':
    main()

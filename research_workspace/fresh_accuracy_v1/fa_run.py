"""有限首轮预算；子进程异常留账，不重跑已经消费的条件。"""
import os
import sys
import subprocess
from fa_common import ROOT, RUN, SEEDS, POLICIES, base, read, save, sha, verify
from fa_stage import prepare
from fa_result import totals

TIMEOUT_SECONDS = 900


def run(script, *args):
    path = RUN/'logs'/('_'.join((script, *map(str, args)))+'.log')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        try:
            result = subprocess.run([sys.executable, '-B', str(ROOT/script), *map(str, args)],
                stdout=stream, stderr=subprocess.STDOUT, timeout=TIMEOUT_SECONDS, check=False)
        except subprocess.TimeoutExpired:
            return dict(ok=False, timeout=True, log=str(path))
    return dict(ok=result.returncode == 0, returncode=result.returncode, log=str(path))


def execute(name, policy):
    worker = run('fa_worker.py', name, policy)
    row = dict(worker=worker, passed=False)
    if worker['ok']:
        row['audit_process'] = run('fa_audit.py', name, policy)
        if row['audit_process']['ok']:
            row.update(verify(base(name, policy)/'audit.json'))
    return row


def condition(case, cameras):
    name, seed = case['item']['id'], case['item']['seed']
    row = dict(id=name, seed=seed, source=case['item']['source'], status='camera_unknown')
    if not cameras[seed]['ok']:
        return row
    camera = read(RUN/'camera_results'/(str(seed)+'.json'))
    if not camera['accepted']:
        return dict(row, status='camera_rejected')
    prepare(case)
    row['qualification_process'] = run('fa_stage.py', 'qualify', name)
    if not row['qualification_process']['ok']:
        return dict(row, status='qualification_unknown')
    qualification = read(base(name, 'original')/'qualification'/str(seed)/'result.json')
    row['qualification_status'] = qualification['status']
    if not qualification['qualified']:
        return dict(row, status='geometry_rejected')
    row['policies'] = {policy: execute(name, policy) for policy in POLICIES}
    row['pair_process'] = run('fa_audit.py', 'pair', name)
    return dict(row, status='paired' if row['pair_process']['ok'] else 'input_pair_error')


def main():
    manifest = verify(RUN/'manifest.json')
    save(RUN/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    cameras = {seed: run('fa_stage.py', 'camera', seed) for seed in SEEDS}
    rows = []
    for case in manifest['cases']:
        if case['item']['group'] != 'varied_noisy':
            continue
        row = condition(case, cameras)
        rows.append(row)
        save(RUN/'rows'/(case['item']['id']+'.json'), row)
        print(dict(id=row['id'], status=row['status'], totals=totals(rows)), flush=True)
    verify(RUN/'manifest.json')
    files = [p for p in RUN.rglob('*.json') if p != RUN/'result.json']
    save(RUN/'result.json', dict(complete=True, rows=rows, totals=totals(rows),
        identities={str(p): sha(p) for p in files}, manifest_sha256=sha(RUN/'manifest.json'),
        physical_attempts=sum(1 for _ in RUN.glob('conditions/*/*/cases/*/first/started.json')),
        model_calls=0, training_updates=0))


if __name__ == '__main__':
    main()

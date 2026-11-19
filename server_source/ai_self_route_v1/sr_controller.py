import os
import subprocess
import sys
import traceback
from sr_common import ROOT, SEEDS, read, save, verify
from nc_common import status


def run(script, args, *, name, timeout):
    status(ROOT/'status.json', dict(stage=name, job=os.environ['SLURM_JOB_ID']))
    with (ROOT/f'{name}.log').open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/script), *args], stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=timeout)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    for seed in SEEDS:
        for case in manifest['cases']:
            if case['item']['seed']==seed:
                name = case['item']['id']
                run('sr_worker.py', [name], name=name, timeout=1800)
        run('sr_audit.py', ['--seed', str(seed)], name=f'audit_{seed}', timeout=1200)
        assert read(ROOT/f'audit_{seed}.json')['passed']
    rows = [r for seed in SEEDS for r in read(ROOT/f'audit_{seed}.json')['rows']]
    attempts = sum(r['attempts'] for r in rows)
    assert attempts <= manifest['max_attempts']
    verify()
    save(ROOT/'complete.json', dict(passed=True, attempts=attempts, rows=rows, model_calls=0, training_ready=False))
    status(ROOT/'status.json', dict(stage='self_guard_pilot_completed', attempts=attempts))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        status(ROOT/'status.json', dict(stage='engineering_failure', error=repr(error)))
        raise

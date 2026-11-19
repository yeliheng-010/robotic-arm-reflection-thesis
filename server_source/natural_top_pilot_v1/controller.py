import os
import subprocess
import sys
import traceback
from nc_common import status
from tp_common import ROOT, read, save, verify


def run(script, args, *, label):
    status(ROOT/'status.json', dict(stage=label, job=os.environ['SLURM_JOB_ID']))
    with (ROOT/(label+'.log')).open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/script), *args], stdout=log,
            stderr=subprocess.STDOUT, check=True, timeout=1800)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    rows = []
    for case in manifest['cases']:
        name = case['item']['id']
        run('worker.py', [name], label=name)
        run('audit.py', ['--case-id', name], label='audit_'+name)
        audit = read(ROOT/'audits'/(name+'.json'))
        assert audit['passed']
        rows.append(audit['row'])
    verify()
    attempts = sum(r['attempts'] for r in rows)
    assert attempts <= manifest['max_attempts']
    save(ROOT/'complete.json', dict(passed=True, rows=rows, attempts=attempts, model_calls=0, training_ready=False))
    status(ROOT/'status.json', dict(stage='completed', attempts=attempts))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise

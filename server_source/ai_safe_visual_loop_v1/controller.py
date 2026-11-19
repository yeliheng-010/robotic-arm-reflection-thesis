import os
import sys
import subprocess
import traceback
from unittest.mock import patch
import nc_controller
from nc_common import status
from sv_common import ROOT, read, save, verify


def run(script, args, *, label):
    status(ROOT/'status.json', dict(stage=label, job=os.environ['SLURM_JOB_ID']))
    with (ROOT/(label+'.log')).open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/script), *args], stdout=log,
            stderr=subprocess.STDOUT, check=True, timeout=2400)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    rows = []
    with (ROOT/'model_service.log').open('x') as log:
        process = subprocess.Popen(['bash', str(ROOT/'model_environment.sh')], stdout=log, stderr=subprocess.STDOUT)
        with patch.object(nc_controller, 'ROOT', ROOT):
            try:
                nc_controller.ready(process)
                for case in manifest['cases']:
                    name = case['item']['id']
                    run('worker.py', [name], label=name)
                    run('audit.py', ['--case-id', name], label='audit_'+name)
                    audited = read(ROOT/'audits'/(name+'.json'))
                    assert audited['passed']
                    rows.append(audited['row'])
            finally:
                clean = nc_controller.stop(process)
    assert clean
    attempts, calls = sum(r['attempts'] for r in rows), sum(r['model_calls'] for r in rows)
    assert attempts <= manifest['max_new_attempts'] and calls <= manifest['max_model_calls']
    assert calls == read(ROOT/'service/stopped.json')['calls']
    assert calls == len(list((ROOT/'service/requests').glob('*_request.json')))
    verify()
    save(ROOT/'complete.json', dict(passed=True, rows=rows, attempts=attempts, model_calls=calls, training_ready=False))
    status(ROOT/'status.json', dict(stage='completed', attempts=attempts, model_calls=calls))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise

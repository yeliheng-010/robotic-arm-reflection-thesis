"""同作业内管理自身模型/仿真进程，阶段门禁与状态持久化。"""
import os
import subprocess
import sys
import time
import traceback
from nc_common import ROOT, SEEDS, read, save, status, verify

STARTUP_SECONDS = 600
CASE_SECONDS = 1200
AUDIT_SECONDS = 900
SHUTDOWN_SECONDS = 30


def run(script, args, *, label, timeout):
    status(ROOT/'status.json', dict(stage=label, job=os.environ['SLURM_JOB_ID']))
    with (ROOT/f'{label}.log').open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/script), *args], stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=timeout)


def ready(process):
    deadline = time.monotonic()+STARTUP_SECONDS
    while not (ROOT/'service/ready.json').exists():
        assert process.poll() is None, 'Model service exited before ready'
        assert time.monotonic() < deadline, 'Model startup timed out'
        time.sleep(1)
    assert read(ROOT/'service/ready.json')['startup_generations'] == 0


def stop(process):
    save(ROOT/'stop_service.json', dict(requested=True))
    forced = False
    try:
        code = process.wait(timeout=SHUTDOWN_SECONDS)
    except subprocess.TimeoutExpired:
        forced = True
        process.terminate()
        try:
            code = process.wait(timeout=SHUTDOWN_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            code = process.wait()
    save(ROOT/'service_exit.json', dict(code=code, forced=forced))
    return code == 0 and not forced


def collect(manifest):
    for seed in SEEDS:
        for case in manifest['cases']:
            if case['item']['seed'] == seed:
                name = case['item']['id']
                run('nc_worker.py', [name], label=name, timeout=CASE_SECONDS)
        run('nc_audit.py', ['--seed', str(seed)], label=f'audit_{seed}', timeout=AUDIT_SECONDS)
        assert read(ROOT/f'audit_{seed}.json')['passed']


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'controller_started.json', dict(job=os.environ['SLURM_JOB_ID']))
    with (ROOT/'model_service.log').open('x') as log:
        process = subprocess.Popen(['bash', str(ROOT/'model_environment.sh')], stdout=log, stderr=subprocess.STDOUT)
        try:
            ready(process)
            collect(manifest)
        finally:
            clean = stop(process)
    assert clean, 'Model service did not stop cleanly'
    audits = [read(ROOT/f'audit_{seed}.json') for seed in SEEDS]
    attempts, calls = sum(r['attempts'] for r in audits), sum(r['model_calls'] for r in audits)
    assert attempts <= manifest['max_new_attempts'] and calls <= manifest['max_model_calls']
    assert calls == read(ROOT/'service/stopped.json')['calls']
    assert calls == len(list((ROOT/'service/requests').glob('*_request.json')))
    verify()
    save(ROOT/'complete.json', dict(passed=True, conditions=8, attempts=attempts, model_calls=calls, training_ready=False))
    status(ROOT/'status.json', dict(stage='pilot_completed', attempts=attempts, model_calls=calls))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'controller_failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        status(ROOT/'status.json', dict(stage='engineering_failure', error=repr(error)))
        raise

"""从审计完成的条件边界续跑，不重放已消费的执行或请求。"""
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import nc_controller
from sv_common import ROOT, read, save, sha, verify

LIFECYCLE = ROOT/'resume_v5'


def audited(name):
    path = ROOT/'audits'/(name+'.json')
    value = read(path)
    assert value['passed'] and value['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in value['identities'].items())
    return value['row']


def prepare(manifest):
    assert read(ROOT/'service/stopped.json')['stopped']
    assert read(ROOT/'service_exit.json') == dict(code=0, forced=False)
    completed, pending = [], []
    for case in manifest['cases']:
        name = case['item']['id']
        if (ROOT/'cases'/name).exists():
            completed.append(audited(name))
        else:
            pending.append(name)
    requests = list((ROOT/'service/requests').glob('*_request.json'))
    assert sum(r['model_calls'] for r in completed) == len(requests)
    assert len(requests) == read(ROOT/'service/stopped.json')['calls']
    paths = [ROOT/'manifest.json', ROOT/'failure.json', ROOT/'service/stopped.json',
        *ROOT.glob('*v5.py'), *ROOT.glob('*v5.sh'), *ROOT.glob('*v5.sbatch')]
    paths += list((ROOT/'audits').glob('*.json'))
    save(LIFECYCLE/'manifest.json', dict(pending=pending, completed=completed,
        previous_model_calls=len(requests), identities={str(p):sha(p) for p in paths},
        parent_job='5964', job=os.environ['SLURM_JOB_ID'], changed_execution=False))
    return pending


def run(script, args, label):
    with (LIFECYCLE/(label+'.log')).open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/script), *args],
            stdout=log, stderr=subprocess.STDOUT, check=True, timeout=2400)


def main():
    manifest = verify()
    pending = prepare(manifest)
    with (LIFECYCLE/'model_service.log').open('x') as log:
        process = subprocess.Popen(['bash', str(ROOT/'resume_model_v5.sh')], stdout=log, stderr=subprocess.STDOUT)
        with patch.object(nc_controller, 'ROOT', LIFECYCLE):
            try:
                nc_controller.ready(process)
                for name in pending:
                    run('worker_v4.py', [name], name)
                    run('audit_v5.py', ['--case-id', name], 'audit_'+name)
                    audited(name)
            finally:
                clean = nc_controller.stop(process)
    assert clean
    rows = [audited(c['item']['id']) for c in manifest['cases']]
    attempts, calls = sum(r['attempts'] for r in rows), sum(r['model_calls'] for r in rows)
    assert attempts <= manifest['max_new_attempts'] and calls <= manifest['max_model_calls']
    assert calls == read(LIFECYCLE/'service/stopped.json')['calls']
    assert calls == len(list((ROOT/'service/requests').glob('*_request.json')))
    verify()
    identities = read(LIFECYCLE/'manifest.json')['identities']
    assert all(sha(p) == h for p,h in identities.items())
    save(ROOT/'complete.json', dict(passed=True, rows=rows, attempts=attempts, model_calls=calls,
        training_ready=False, continuation=str(LIFECYCLE/'manifest.json'), identities=identities))


if __name__ == '__main__':
    main()

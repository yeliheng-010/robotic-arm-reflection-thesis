import os
import sys
import subprocess
import traceback
from collection_common import ROOT, PHYSICS, save, sha, verify


def run(script, args, *, label):
    with (PHYSICS/(label+'.log')).open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/script), *args],
            stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify(PHYSICS/'manifest.json')
    save(PHYSICS/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    rows = []
    for case in manifest['cases']:
        name = case['item']['id']
        run('collect_worker.py', [name], label=name)
        run('collect_audit.py', [name], label='audit_'+name)
        audit = verify(PHYSICS/'audits'/(name+'.json'))
        assert audit['passed']
        rows.append(audit['row'])
        print(dict(id=name, attempts=rows[-1]['attempts'], audited=True), flush=True)
    attempts = sum(r['attempts'] for r in rows)
    assert attempts <= manifest['max_attempts']
    verify(PHYSICS/'manifest.json')
    save(PHYSICS/'complete.json', dict(passed=True, rows=rows, attempts=attempts, model_calls=0,
        manifest_sha256=sha(PHYSICS/'manifest.json'), training_ready=False))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(PHYSICS/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise

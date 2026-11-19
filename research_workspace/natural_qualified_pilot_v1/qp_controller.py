import os
import subprocess
import sys
import traceback
from qp_common import ROOT,read,save,verify
from nc_common import status


def run(script,args,*,name,timeout):
    status(ROOT/'status.json',dict(stage=name,job=os.environ['SLURM_JOB_ID']))
    with (ROOT/(name+'.log')).open('x') as log:
        subprocess.run([sys.executable,'-B',str(ROOT/script),*args],stdout=log,
            stderr=subprocess.STDOUT,check=True,timeout=timeout)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest=verify()
    save(ROOT/'started.json',dict(job=os.environ['SLURM_JOB_ID']))
    rows=[]
    for case in manifest['cases']:
        name=case['item']['id']
        run('qp_worker.py',[name],name=name,timeout=1800)
        run('qp_audit.py',['--case-id',name],name='audit_'+name,timeout=1200)
        audited=read(ROOT/'audits'/(name+'.json'))
        assert audited['passed']
        rows.append(audited['row'])
    verify()
    attempts=sum(r['attempts'] for r in rows)
    assert attempts<=manifest['max_attempts']
    save(ROOT/'complete.json',dict(passed=True,rows=rows,attempts=attempts,model_calls=0,training_ready=False))
    status(ROOT/'status.json',dict(stage='qualified_pilot_complete',attempts=attempts))


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json',dict(error=repr(error),traceback=traceback.format_exc()))
        status(ROOT/'status.json',dict(stage='engineering_failure',error=repr(error)))
        raise

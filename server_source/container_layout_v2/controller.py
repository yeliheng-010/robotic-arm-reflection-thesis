"""独立Slurm协调；任何工程失败停后继，保留进度供次日验收。"""
import os
import subprocess
import time
from cl_common import read,save,sha,verify
from cl_design import ROOT

POLL_SECONDS=10
DEADLINE_SECONDS=8*60*60
ACCOUNTING_GRACE=120
STAGES=(('smoke','physics.sbatch',('smoke',)),('smoke_audit','audit.sbatch',('smoke',)),
        ('batch','physics.sbatch',('batch',)),('final_audit','audit.sbatch',('final',)))


def active(job):
    return bool(subprocess.check_output(['squeue','-h','-j',job,'-o','%i'],text=True).strip())


def wait_job(job,deadline):
    missing=None
    while time.monotonic()<deadline:
        result=subprocess.check_output(['sacct','-X','-n','-P','-j',job,
            '--format=JobIDRaw,State,ExitCode'],text=True)
        rows=[r.split('|')[:3] for r in result.splitlines() if r.strip()]
        bad=[r for r in rows if r[1] not in ('PENDING','RUNNING','CONFIGURING','COMPLETING','COMPLETED')]
        assert not bad,str(bad)
        if not active(job):
            if rows:
                assert all(r[1:]==['COMPLETED','0:0'] for r in rows),str(rows)
                return rows
            missing=missing or time.monotonic()
            assert time.monotonic()-missing<ACCOUNTING_GRACE,'Accounting unavailable'
        time.sleep(POLL_SECONDS)
    raise TimeoutError('Controller deadline reached')


def main():
    verify()
    with (ROOT/'submission_started.txt').open('x') as stream:
        stream.write('No silent retries.\n')
    jobs=dict(controller=os.environ['SLURM_JOB_ID'])
    save(ROOT/'jobs.json',jobs)
    status=dict(status='running',started_at=time.time(),manifest_sha256=sha(ROOT/'manifest.json'))
    deadline=time.monotonic()+DEADLINE_SECONDS
    job=None
    try:
        for name,script,args in STAGES:
            job=subprocess.check_output(['sbatch','--parsable',str(ROOT/script),*args],text=True).strip().split(';')[0]
            assert job.isdigit()
            jobs[name]=job
            save(ROOT/'jobs.json',jobs)
            status.update(stage=name,active_job=job)
            save(ROOT/'STATUS.json',status)
            rows=wait_job(job,deadline)
            status.setdefault('completed_stages',[]).append(dict(stage=name,job=job,accounting=rows))
        final=read(ROOT/'verification.json')
        assert final['passed'] and final['complete'] and final['accounted']==160
        status.update(status='completed',stage='finished',active_job=None)
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        if job and active(job):
            subprocess.run(['scancel',job],check=False)
        raise
    finally:
        status['ended_at']=time.time()
        save(ROOT/'STATUS.json',status)


if __name__=='__main__':
    main()

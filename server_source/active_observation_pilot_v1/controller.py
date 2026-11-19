"""CPU协调四卡资格试验；实际终态验收后再提交后继。"""
import os
import subprocess
import time
from ap_common import ROOT,read,save,verify,sha

POLL_SECONDS=10
DEADLINE_SECONDS=4*60*60
ACCOUNTING_GRACE=120
STAGES=(('smoke','run.sbatch','smoke'),('gate','audit.sbatch','smoke'),
        ('batch','run.sbatch','batch'),('audit','audit.sbatch','final'))


def active(job):
    return bool(subprocess.check_output(['squeue','-h','-j',job,'-o','%i'],text=True).strip())


def wait_job(job,deadline):
    missing=None
    while time.monotonic()<deadline:
        if not active(job):
            text=subprocess.check_output(['sacct','-X','-n','-P','-j',job,'--format=JobIDRaw,State,ExitCode'],text=True)
            rows=[r.split('|')[:3] for r in text.splitlines() if r.strip()]
            if rows:
                assert all(r[1:] == ['COMPLETED','0:0'] for r in rows),str(rows)
                return rows
            missing=missing or time.monotonic()
            assert time.monotonic()-missing<ACCOUNTING_GRACE,'Accounting unavailable'
        time.sleep(POLL_SECONDS)
    raise TimeoutError('Controller deadline reached')


def main():
    verify()
    with (ROOT/'submission_started.txt').open('x') as stream:
        stream.write('Single submission; no silent retries.\n')
    jobs=read(ROOT/'jobs.json')
    assert jobs['controller']==os.environ['SLURM_JOB_ID']
    status=dict(status='running',manifest_sha256=sha(ROOT/'manifest.json'),started_at=time.time())
    deadline=time.monotonic()+DEADLINE_SECONDS
    job=None
    try:
        for name,script,phase in STAGES:
            job=subprocess.check_output(['sbatch','--parsable',str(ROOT/script),phase],text=True).strip().split(';')[0]
            assert job.isdigit()
            jobs[name]=job
            save(ROOT/'jobs.json',jobs)
            status.update(stage=name,active_job=job)
            save(ROOT/'STATUS.json',status)
            rows=wait_job(job,deadline)
            status.setdefault('completed_stages',[]).append(dict(stage=name,job=job,accounting=rows))
        final=read(ROOT/'verification.json')
        assert final['passed'] and final['complete'] and final['accounted']==24
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

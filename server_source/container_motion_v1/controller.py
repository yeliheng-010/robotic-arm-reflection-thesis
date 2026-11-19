"""CPU协调，无人值守门控；只取消自身提交的当前作业。"""
import os
import subprocess
import time
from cm_common import ROOT, verify, read, save, sha
from cd_controller_wait import active, wait_job

DEADLINE_SECONDS = 6*60*60
STAGES = (('development','physics.sbatch',('development',)),
    ('development_audit','audit.sbatch',('development',)),
    ('smoke','physics.sbatch',('smoke',)),('smoke_audit','audit.sbatch',('smoke',)),
    ('batch','physics.sbatch',('batch',)),('final_audit','audit.sbatch',('final',)))


def submit_stage(name, script, args, *, jobs, status, deadline):
    job = subprocess.check_output(['sbatch','--parsable',str(ROOT/script),*args],text=True).strip().split(';')[0]
    assert job.isdigit()
    jobs[name]=job
    save(ROOT/'jobs.json',jobs)
    status.update(stage=name,active_job=job)
    save(ROOT/'STATUS.json',status)
    rows = wait_job(job,deadline)
    status.setdefault('completed_stages',[]).append(dict(stage=name,job=job,accounting=rows))


def main():
    verify()
    with (ROOT/'submission_started.txt').open('x') as stream:
        stream.write('Single submission; no silent retries.\n')
    jobs = read(ROOT/'jobs.json')
    assert jobs['controller']==os.environ['SLURM_JOB_ID']
    status = dict(status='running',started_at=time.time(),manifest_sha256=sha(ROOT/'manifest.json'))
    deadline = time.monotonic()+DEADLINE_SECONDS
    try:
        for name,script,args in STAGES:
            submit_stage(name,script,args,jobs=jobs,status=status,deadline=deadline)
            if name=='development_audit' and not read(ROOT/'gate_development.json')['promote']:
                status.update(status='development_completed',stage='no_promotion',active_job=None)
                return
        final = read(ROOT/'verification.json')
        assert final['passed'] and final['complete'] and final['accounted']==80
        status.update(status='completed',stage='finished',active_job=None)
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        job = status.get('active_job')
        if job and active(job):
            subprocess.run(['scancel',job],check=False)
        raise
    finally:
        status['ended_at']=time.time()
        save(ROOT/'STATUS.json',status)


if __name__=='__main__':
    main()

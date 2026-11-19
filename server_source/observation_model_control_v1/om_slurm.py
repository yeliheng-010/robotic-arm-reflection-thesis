"""仅管理本轮显式提交的作业；排队与执行都有总超时。"""
import subprocess
import time
from om_common import ROOT,save

POLL_SECONDS=10
ACCOUNTING_GRACE_SECONDS=120


def submit(script,*arguments):
    output=subprocess.check_output(['sbatch','--parsable',str(ROOT/script),*arguments],text=True).strip()
    job=output.split(';')[0]
    assert job.isdigit()
    return job


def active(job):
    return bool(subprocess.check_output(['squeue','--noheader','--jobs',job,'--format=%i'],text=True).strip())


def records(job):
    output=subprocess.check_output(['sacct','-X','-n','-P','-j',job,
                                    '--format=JobIDRaw,State,ExitCode'],text=True)
    return [dict(zip(('job','state','exit_code'),line.split('|')[:3]))
            for line in output.splitlines() if line.strip()]


def wait_job(job,*,service,deadline):
    missing_since=None
    while True:
        assert service.poll() is None,'Model subprocess stopped unexpectedly'
        assert time.monotonic()<deadline,'Overall unattended deadline exceeded'
        if not active(job):
            rows=records(job)
            if rows:
                assert all(r['state']=='COMPLETED' and r['exit_code']=='0:0' for r in rows),str(rows)
                return rows
            missing_since=missing_since or time.monotonic()
            assert time.monotonic()-missing_since<ACCOUNTING_GRACE_SECONDS,'Slurm accounting unavailable'
        time.sleep(POLL_SECONDS)


def cancel_owned(jobs):
    outcomes=[]
    for name,job in jobs.items():
        if name in ('preflight','service'):
            continue
        if active(job):
            result=subprocess.run(['scancel',job],capture_output=True,text=True)
            outcomes.append(dict(name=name,job=job,returncode=result.returncode))
    save(ROOT/'cleanup_jobs.json',outcomes)

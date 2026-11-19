"""Slurm服务作业内独立协调，无需本地浏览器维持连接。"""
import os
import subprocess
import time
import traceback
from am_common import ROOT,PARENT,read,save,verify,sha
from am_client import ready
from am_slurm import submit,wait_job,cancel_owned

MODEL_PYTHON=str(PARENT/'qwen35/env/bin/python')
STARTUP_SECONDS=900
OVERALL_SECONDS=7*60*60
STAGES=(('smoke','run.sbatch','smoke'),('smoke_audit','audit.sbatch','smoke'),
        ('batch','run.sbatch','batch'),('final_audit','audit.sbatch','final'))


def wait_ready(service):
    deadline=time.monotonic()+STARTUP_SECONDS
    while True:
        assert service.poll() is None,'Model failed during startup'
        try:
            return ready()
        except Exception:
            assert time.monotonic()<deadline,'Model readiness timed out'
            time.sleep(3)


def run_stages(service,jobs,status):
    deadline=time.monotonic()+OVERALL_SECONDS
    status['health']=wait_ready(service)
    for name,script,phase in STAGES:
        assert service.poll() is None
        job=submit(script,phase)
        jobs[name]=job
        save(ROOT/'jobs.json',jobs)
        status.update(stage=name,active_job=job,updated_at=time.time())
        save(ROOT/'STATUS.json',status)
        completed=wait_job(job,service=service,deadline=deadline)
        status.setdefault('completed_stages',[]).append(dict(stage=name,job=job,accounting=completed))
        save(ROOT/'STATUS.json',status)
    result=read(ROOT/'verification.json')
    assert result['passed'] and result['complete'] and result['accounted']==24


def stop_service(service):
    save(ROOT/'stop_service.json',dict(reason='Orchestrator completed or failed',at=time.time()))
    try:
        service.wait(timeout=30)
    except subprocess.TimeoutExpired:
        service.terminate()
        try:
            service.wait(timeout=15)
        except subprocess.TimeoutExpired:
            service.kill()
            service.wait(timeout=15)
    save(ROOT/'service/process_exit.json',dict(returncode=service.returncode,at=time.time()))


def main():
    verify()
    assert os.environ.get('SLURM_JOB_ID')
    with (ROOT/'orchestration_started.txt').open('x') as stream:
        stream.write('Single submission; never retry automatically.\n')
    jobs=read(ROOT/'jobs.json')
    assert jobs['service']==os.environ['SLURM_JOB_ID']
    status=dict(status='running',stage='model_startup',started_at=time.time(),
                manifest_sha256=sha(ROOT/'manifest.json'),test_used=False,training_started=False)
    save(ROOT/'STATUS.json',status)
    with (ROOT/'model.log').open('x') as stream:
        service=subprocess.Popen([MODEL_PYTHON,str(ROOT/'model_service.py')],stdout=stream,stderr=subprocess.STDOUT)
        try:
            run_stages(service,jobs,status)
            status.update(status='completed',stage='finished',active_job=None)
        except BaseException as error:
            status.update(status='failed',error=repr(error),traceback=traceback.format_exc())
            cancel_owned(jobs)
            raise
        finally:
            stop_service(service)
            status.update(ended_at=time.time(),service_returncode=service.returncode)
            save(ROOT/'STATUS.json',status)
            (ROOT/'RUN_STATUS.md').write_text('# 无人值守运行状态\n\n'+
                f"状态：{status['status']}；最后阶段：{status['stage']}。\n\n"+
                '详情见 STATUS.json、jobs.json、REPORT.md 和各阶段 verification 文件。\n')


if __name__=='__main__':
    main()

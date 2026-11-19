"""Submit an overnight batch; all children are detached Slurm jobs."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from training.overnight.dataset import atomic


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--deadline', required=True, help='ISO timestamp with explicit timezone')
    p.add_argument('--after-job', required=True, help='Existing Qwen smoke job; never cancels it')
    a = p.parse_args()
    parsed = datetime.fromisoformat(a.deadline)
    if parsed.tzinfo is None:
        p.error('--deadline requires a timezone')
    deadline = parsed.timestamp()
    if deadline <= time.time()+300:
        p.error('Deadline is too close or has passed')
    root = Path(__file__).resolve().parents[2]
    output = a.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    state_path = output/'jobs.json'
    if state_path.exists():
        print(state_path.read_text())
        return
    if not a.after_job.isdecimal():
        p.error('--after-job must be a Slurm numeric job id')
    identity = subprocess.run(['sacct', '-X', '-j', a.after_job, '--noheader', '--parsable2',
        '--format=User%40,JobName%100'], capture_output=True, text=True, check=True).stdout
    if not any(line.strip().split('|')[:2] == ['yeliheng', 'qwen35-retry'] for line in identity.splitlines()):
        raise RuntimeError('Dependency is not the intended existing Qwen smoke job')
    env = dict(os.environ, GRASP_NIGHT_CODE=str(root), GRASP_NIGHT_OUTPUT=str(output),
               GRASP_NIGHT_DEADLINE=str(deadline))
    submitted = []
    try:
        def submit(script, dependency, **extra):
            current = dict(env, **extra)
            result = subprocess.run(['sbatch', '--parsable', '--nodelist=gpu',
                '--dependency=afterany:'+dependency, '--export=ALL',
                str(root/'training/overnight'/script)], env=current, capture_output=True, text=True, check=True)
            job = result.stdout.strip().split(';')[0]
            if not job.isdecimal():
                raise RuntimeError('Unexpected sbatch response: '+result.stdout)
            submitted.append(job)
            return job
        teacher = submit('teacher.slurm', a.after_job)
        collector = submit('collect.slurm', a.after_job, GRASP_TEACHER_JOB=teacher)
        finalizer = submit('finalize.slurm', collector, GRASP_TEACHER_JOB=teacher)
        jobs = dict(output=str(output), code=str(root), teacher_job=teacher,
                    collection_job=collector, report_job=finalizer, after_job=a.after_job,
                    deadline=a.deadline, deadline_epoch=deadline, planned_tasks=480, submitted=time.time())
        atomic(state_path, jobs)
        atomic(Path('/home/yeliheng/grasp_server/latest_overnight.json'), jobs)
        print(json.dumps(jobs, ensure_ascii=False, indent=2))
    except BaseException:
        for job in reversed(submitted):
            subprocess.run(['scancel', job], check=False)
        raise


if __name__ == '__main__':
    main()

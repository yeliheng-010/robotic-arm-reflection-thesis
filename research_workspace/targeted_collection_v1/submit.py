"""仅提交一次，逐步落盘作业号，不重复启动已有试采。"""
import json
import subprocess
from pilot_common import ROOT, verify, save


def submit():
    verify()
    with (ROOT/'submission_started.json').open('x') as stream:
        json.dump(dict(status='submitting'), stream)
    jobs = {}
    chain = [('smoke', 'run.sbatch', 'smoke', None),
             ('gate', 'audit.sbatch', 'smoke', 'afterok:smoke'),
             ('batch', 'run.sbatch', 'batch', 'afterok:gate'),
             ('audit', 'audit.sbatch', 'final', 'afterany:batch')]
    for name, script, phase, dependency in chain:
        command = ['sbatch', '--parsable']
        if dependency:
            mode, parent = dependency.split(':')
            command.append(f'--dependency={mode}:{jobs[parent]}')
        value = subprocess.check_output(command+[str(ROOT/script), phase], text=True).strip()
        job = value.split(';')[0]
        assert job.isdigit()
        jobs[name] = job
        save(ROOT/'jobs.json', jobs)
    print(jobs)


if __name__ == '__main__':
    submit()

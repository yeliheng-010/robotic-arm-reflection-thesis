"""服务验收后仅提交一次冒烟、门槛、批量和最终审计。"""
import subprocess
from common import ROOT, verify, read, save
from client import ready


def main():
    verify()
    ready()
    with (ROOT/'batch_submission_started.txt').open('x') as stream:
        stream.write('Do not duplicate this chain.\n')
    jobs = read(ROOT/'jobs.json')
    chain = [('smoke','run.sbatch','smoke',None),
             ('gate','audit.sbatch','smoke','afterok:smoke'),
             ('batch','run.sbatch','batch','afterok:gate'),
             ('audit','audit.sbatch','final','afterany:batch')]
    for name, script, phase, dependency in chain:
        command = ['sbatch','--parsable','--kill-on-invalid-dep=yes']
        if dependency:
            mode, parent = dependency.split(':')
            command.append('--dependency='+mode+':'+jobs[parent])
        result = subprocess.check_output(command+[str(ROOT/script),phase], text=True).strip().split(';')[0]
        assert result.isdigit()
        jobs[name] = result
        save(ROOT/'jobs.json',jobs)
    print(jobs,flush=True)


if __name__ == '__main__':
    main()

"""冻结后仅提交一次完整依赖链，冒烟失败阻止正式训练。"""
import subprocess
from set_common import ROOT, verify, save


def submit():
    verify()
    with (ROOT/'submission_started.txt').open('x') as stream:
        stream.write('Do not duplicate these jobs.\n')
    jobs = {}
    chain = [('smoke','gpu.sbatch','smoke',None,False),
             ('train','gpu.sbatch','train','afterok:smoke',False),
             ('before','gpu.sbatch','before','afterok:smoke',True),
             ('after','gpu.sbatch','after','afterok:train',True),
             ('audit','cpu.sbatch','audit','afterany:before,after',False)]
    for name, script, phase, dependency, array in chain:
        command = ['sbatch','--parsable']
        if array:
            command += ['--array=0-2%3']
        if dependency:
            mode, parents = dependency.split(':')
            command.append('--dependency='+mode+':'+':'.join(jobs[p] for p in parents.split(',')))
        result = subprocess.check_output(command+[str(ROOT/script),phase], text=True).strip().split(';')[0]
        assert result.isdigit()
        jobs[name] = result
        save(ROOT/'jobs.json', jobs)
    print(jobs, flush=True)


if __name__ == '__main__':
    submit()

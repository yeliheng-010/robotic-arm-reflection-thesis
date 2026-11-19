"""预检通过后提交一次CPU控制器，不依赖本机连接。"""
import subprocess
from cd_common import ROOT, gate, save, verify


def main():
    verify()
    gate('preflight.json')
    with (ROOT/'submission_lock.txt').open('x') as stream:
        stream.write('single submission\n')
    job = subprocess.check_output(['sbatch','--hold','--parsable',str(ROOT/'controller.sbatch')],text=True).strip().split(';')[0]
    assert job.isdigit()
    save(ROOT/'jobs.json',dict(controller=job))
    subprocess.run(['scontrol','release',job],check=True)
    print(job,flush=True)


if __name__=='__main__':
    main()

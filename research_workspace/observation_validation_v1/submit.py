"""冻结核验后一次提交依赖链，失败不继续批量。"""
import subprocess
from pilot import ROOT,verify,save,read


def main():
    verify()
    with (ROOT/'submission_started.txt').open('x') as stream:
        stream.write('Do not resubmit automatically.\n')
    jobs=read(ROOT/'jobs.json')
    phases=(('smoke','run.sbatch','smoke','preflight'),('gate','audit.sbatch','smoke','smoke'),
            ('batch','run.sbatch','batch','gate'),('audit','audit.sbatch','final','batch'))
    for name,script,phase,parent in phases:
        mode='afterany' if name=='audit' else 'afterok'
        command=['sbatch','--parsable','--kill-on-invalid-dep=yes',
                 '--dependency='+mode+':'+jobs[parent],str(ROOT/script),phase]
        job=subprocess.check_output(command,text=True).strip().split(';')[0]
        assert job.isdigit()
        jobs[name]=job
        save(ROOT/'jobs.json',jobs)
    print(jobs,flush=True)


if __name__=='__main__':
    main()

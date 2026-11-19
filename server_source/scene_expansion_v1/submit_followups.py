"""仅提交一次依赖链；每次成功提交立刻记录，避免重复作业。"""
import argparse
import json
import subprocess
from expand.design import ROOT
from stability.collection_status import atomic


def submit(script,dependency,*,argument=None):
    command=['sbatch','--parsable',f'--dependency={dependency}',
             '--kill-on-invalid-dep=yes',str(ROOT/script)]
    if argument:
        command.append(argument)
    result=subprocess.run(command,check=True,capture_output=True,text=True)
    job=result.stdout.strip().split(';')[0]
    assert job.isdigit(),result.stdout
    return job


def main(smoke):
    path=ROOT/'jobs.json'
    value=dict(qual_smoke=str(smoke))
    with path.open('x') as stream:
        json.dump(value,stream)
    chain=(('qual_smoke_gate','gate.sbatch','qual_smoke','afterok'),
           ('qualification','run.sbatch','qualification','afterok'),
           ('qualification_gate','gate.sbatch','qualification','afterok'),
           ('loop_smoke','run.sbatch','loop_smoke','afterok'),
           ('loop_smoke_gate','gate.sbatch','loop_smoke','afterok'),
           ('batch','run.sbatch','batch','afterok'),
           ('final_audit','audit.sbatch',None,'afterany'))
    previous=str(smoke)
    for key,script,argument,kind in chain:
        previous=submit(script,f'{kind}:{previous}',argument=argument)
        value[key]=previous
        atomic(path,value)
        print(key,previous,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke-job',required=True,type=int)
    main(parser.parse_args().smoke_job)

"""每个分支从冻结初态重置，独立进程且只执行一次。"""
import os
import sys
from loopstudy import episode
from cl_worker import bound
from cd_common import ROOT, LAYOUT, verify, read, save, gate
from cd_physics_audit import audit_result


def main(index):
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    gate('gate_model.json')
    branch = manifest['branches'][index]
    case = manifest['cases'][branch['case_index']]
    item = case['source']['item']
    layout = read(LAYOUT/'plan.json')['layouts'][str(item['seed'])]
    folder = ROOT/'tasks'/f'{index:03d}'
    folder.mkdir(parents=True,exist_ok=False)
    with bound(item,layout):
        step = episode.attempt(item,branch['action']['state'],directory=folder/'attempt_3',index=3)
    result = dict(branch=branch,step=step,status='completed',test_used=False,
        training_approved=False,extra_observations=0)
    save(folder/'result.json',result)
    save(folder/'summary.json',audit_result(result,branch,manifest))


if __name__ == '__main__':
    main(int(sys.argv[1]))

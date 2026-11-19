"""复用冻结首次执行，仅对初次失败做真实物理恢复。"""
import os
import sys
from copy import deepcopy
from loopstudy import episode
from cl_worker import bound
from rc_common import ROOT,SOURCE,METHODS,MAX_ATTEMPTS,ALIAS,verify,read,save
from rc_policy import decide


def rollout(source,layout,*,method,directory):
    directory.mkdir(parents=True,exist_ok=False)
    steps,decisions=[deepcopy(source['step'])],[]
    result=dict(item=source['item'],method=method,attempts=steps,decisions=decisions,
        model=ALIAS if method=='model' else None,source_index=source['index'],
        test_used=False,training_approved=False,extra_observations=0)
    with bound(source['item'],layout):
        while not steps[-1]['success'] and len(steps)<MAX_ATTEMPTS:
            decision=decide(steps,decisions,method=method)
            decisions.append(decision)
            save(directory/'progress.json',result)
            assert not decision.get('service_failure'),str(decision)
            if decision['selected'] is None:
                break
            index=len(steps)+1
            step=episode.attempt(source['item'],decision['selected']['state'],
                directory=directory/f'attempt_{index}',index=index)
            steps.append(step)
    result.update(status='completed',success=steps[-1]['success'])
    save(directory/'result.json',result)
    return result


def execute(index,manifest=None):
    assert os.environ.get('SLURM_JOB_ID'),'Use Slurm'
    manifest=manifest or verify()
    source=manifest['rows'][index]
    plan=read(SOURCE/'plan.json')
    layout=plan['layouts'][str(source['item']['seed'])]
    directory=ROOT/'tasks'/source['item']['id']
    directory.mkdir(parents=True,exist_ok=False)
    for method in METHODS:
        rollout(source,layout,method=method,directory=directory/method)
    from rc_audit import audit_scene
    save(directory/'summary.json',audit_scene(index,manifest))


if __name__=='__main__':
    execute(int(sys.argv[1]))

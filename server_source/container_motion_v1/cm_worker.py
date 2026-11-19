"""相同预算和原反馈；只在最后一轮增加几何动作适配。"""
import os
import sys
from loopstudy import episode
from loopstudy.actions import initial
from cl_worker import bound
from cl_geometry import verify_compiled
from rc_policy import decide
from cm_common import ROOT, METHODS, verify, read, save, gate
from cm_runtime import attempt


def development(index, manifest):
    case = manifest['cases'][index]
    source = case['source']
    item = source['item']
    layout = manifest['development_plan']['layouts'][str(item['seed'])]
    folder = ROOT/'development'/item['id']
    folder.mkdir(parents=True,exist_ok=False)
    steps = {}
    with bound(item,layout):
        for method in METHODS:
            steps[method] = attempt(item,case['rule_action']['state'],directory=folder/method,
                policy=method,feedback=case['snapshot']['feedback'])
    result = dict(index=index,item=item,steps=steps,status='completed',test_used=False,training_approved=False)
    save(folder/'result.json',result)
    return result


def final_steps(item, shared, decisions, *, folder):
    if len(shared)==1 or shared[-1]['success'] or not decisions[-1]['selected']:
        return {method:list(shared) for method in METHODS}
    steps = {}
    state = decisions[-1]['selected']['state']
    for method in METHODS:
        step = attempt(item,state,directory=folder/method,policy=method,feedback=shared[-1]['feedback'])
        steps[method] = list(shared)+[step]
    return steps


def shared_steps(item, folder):
    shared = [episode.attempt(item,initial(),directory=folder/'initial',index=1)]
    decisions = []
    if shared[0]['success']:
        return shared,decisions
    decision = decide(shared,decisions,method='rule')
    decisions.append(decision)
    if decision['selected'] is None:
        return shared,decisions
    shared.append(episode.attempt(item,decision['selected']['state'],directory=folder/'second',index=2))
    if not shared[-1]['success']:
        decisions.append(decide(shared,decisions,method='rule'))
    return shared,decisions


def validation(index, manifest):
    gate('gate_development.json')
    assert read(ROOT/'gate_development.json')['promote']
    plan = manifest['validation_plan']
    item = plan['items'][index]
    layout = plan['layouts'][str(item['seed'])]
    assert layout['accepted'], 'Geometry rejection must be handled before execution'
    geometry = verify_compiled(item,layout,plan['geometry'])
    folder = ROOT/'validation'/item['id']
    folder.mkdir(parents=True,exist_ok=False)
    with bound(item,layout):
        shared,decisions = shared_steps(item,folder)
        steps = final_steps(item,shared,decisions,folder=folder)
    source = dict(index=index,item=item,step=shared[0],geometry=geometry,success=shared[0]['success'])
    result = dict(index=index,item=item,source=source,shared=shared,decisions=decisions,steps=steps,
        status='completed',test_used=False,training_approved=False)
    save(folder/'result.json',result)
    return result


if __name__=='__main__':
    assert os.environ.get('SLURM_JOB_ID')
    phase,index = sys.argv[1],int(sys.argv[2])
    manifest = verify()
    if phase=='development':
        development(index,manifest)
    else:
        assert phase in ('smoke','batch')
        validation(index,manifest)

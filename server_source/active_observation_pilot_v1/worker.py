"""两种观测分配规则共享初态，后续动作独立执行。"""
import argparse
from copy import deepcopy
from unittest.mock import patch
from hardstudy import qualify
from hardstudy.intervention import attempt
from ap_common import ROOT,verify,save,METHODS,MAX_ATTEMPTS
from ap_policy import observe,decide


def rollout(item,first,*,directory,method):
    directory.mkdir(parents=True,exist_ok=False)
    steps,decisions=[deepcopy(first)],[]
    used=0
    result=dict(item=item,attempts=steps,decisions=decisions,method=method,model=None,
        test_used=False,training_approved=False,source='active_observation_rule_qualification')
    while not steps[-1]['success'] and len(steps)<MAX_ATTEMPTS:
        observation=observe(steps[-1],item,method=method,used=used)
        used+=observation['extra_cost']
        d=decide(steps[-1],observation)
        decisions.append(d)
        save(directory/'progress.json',result)
        if d['selected'] is None:
            break
        index=len(steps)+1
        steps.append(attempt(item,d['selected']['state'],directory=directory/f'attempt_{index}',index=index))
    result.update(success=steps[-1]['success'],status='completed',extra_observations=used)
    save(directory/'result.json',result)
    return result


def execute(index):
    scene=verify()['scenes'][index]
    directory=ROOT/'tasks'/scene['id']
    directory.mkdir(parents=True,exist_ok=False)
    with patch.object(qualify,'ROOT',ROOT):
        q=qualify.run(scene)
    value=dict(scene=scene,eligible=q['eligible'],trajectories=[],status='running',model=None,
        test_used=False,training_approved=False,source='active_observation_rule_qualification')
    if q['eligible']:
        item=dict(scene,id=scene['id']+'_qualification',arm='new_rule')
        for method in METHODS:
            rollout(item,q['steps'][1],directory=directory/method,method=method)
            value['trajectories'].append(str(directory/method/'result.json'))
    value['status']='completed'
    save(directory/'result.json',value)
    from ap_audit import audit_scene
    save(directory/'summary.json',audit_scene(value))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('index',type=int)
    execute(parser.parse_args().index)

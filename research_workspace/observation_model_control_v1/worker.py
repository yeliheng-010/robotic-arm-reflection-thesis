"""一条件一个进程，四方法共享初始失败，后续单独执行。"""
import argparse
from copy import deepcopy
from unittest.mock import patch
from hardstudy import qualify
from hardstudy.intervention import attempt
from om_common import ROOT,verify,save,METHODS,MAX_ATTEMPTS,ALIASES
from om_policy import observe,decide


def rollout(item,first,*,directory,method):
    directory.mkdir(parents=True,exist_ok=False)
    steps,decisions=[deepcopy(first)],[]
    used=0
    result=dict(item=item,attempts=steps,decisions=decisions,method=method,
        model=ALIASES['base'] if method.startswith('base_') else None,
        test_used=False,training_approved=False,source='observation_processing_selector_control')
    while not steps[-1]['success'] and len(steps)<MAX_ATTEMPTS:
        observation=observe(steps[-1],item,method=method,used=used)
        used+=observation['extra_cost']
        decision=decide(steps[-1],observation,method=method)
        decisions.append(decision)
        save(directory/'progress.json',result)
        assert not decision.get('service_failure'),'Model transport failure; preserve partial execution'
        if decision['selected'] is None:
            break
        index=len(steps)+1
        steps.append(attempt(item,decision['selected']['state'],directory=directory/f'attempt_{index}',index=index))
    result.update(success=steps[-1]['success'],status='completed',extra_observations=used)
    save(directory/'result.json',result)
    return result


def execute(index):
    scene=verify()['scenes'][index]
    directory=ROOT/'tasks'/scene['id']
    directory.mkdir(parents=True,exist_ok=False)
    with patch.object(qualify,'ROOT',ROOT):
        q=qualify.run(scene)
    value=dict(scene=scene,eligible=q['eligible'],trajectories=[],status='running',
        source='observation_processing_selector_control',test_used=False,training_approved=False)
    if q['eligible']:
        item=dict(scene,id=scene['id']+'_qualification',arm='new_rule')
        for method in METHODS:
            rollout(item,q['steps'][1],directory=directory/method,method=method)
            value['trajectories'].append(str(directory/method/'result.json'))
    value['status']='completed'
    save(directory/'result.json',value)
    from om_audit import audit_scene
    save(directory/'summary.json',audit_scene(value))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('index',type=int)
    execute(parser.parse_args().index)

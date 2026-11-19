"""一次资格条件一个进程，观测与执行使用分开的账本。"""
import argparse
from copy import deepcopy
from unittest.mock import patch
from hardstudy import qualify
from hardstudy.intervention import attempt
from pilot import ROOT,verify,save,MAX_ATTEMPTS
from policy import modes,observe,decide,branch_target


def rollout(item,prefix,*,directory,mode,alternate=None):
    directory.mkdir(parents=True,exist_ok=False)
    steps,decisions=deepcopy(prefix)
    used=sum(d['observation']['extra_cost'] for d in decisions)
    override_at=len(steps) if alternate is not None else None
    result=dict(item=item,attempts=steps,decisions=decisions,mode=mode,override_at=override_at,
                model=None,test_used=False,training_approved=False,source='synthetic_sensor_rule_qualification')
    while not steps[-1]['success'] and len(steps)<MAX_ATTEMPTS[item['mechanism']]:
        observation=observe(steps[-1],item,mode=mode,used=used)
        used+=observation['extra_cost']
        decision=decide(steps[-1],observation,alternate=alternate if len(steps)==override_at else None)
        decisions.append(decision)
        save(directory/'progress.json',result)
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
        qualification=qualify.run(scene)
    value=dict(scene=scene,eligible=qualification['eligible'],trajectories=[],status='running',
               model=None,test_used=False,training_approved=False)
    if qualification['eligible']:
        item=dict(scene,id=scene['id']+'_qualification',arm='new_rule')
        for mode in modes(item):
            path=directory/mode
            trace=rollout(item,([qualification['steps'][1]],[]),directory=path,mode=mode)
            value['trajectories'].append(str(path/'result.json'))
            if item['mechanism']=='side_effect' and branch_target(trace):
                offset,target=branch_target(trace)
                rollout(item,(trace['attempts'][:offset+1],trace['decisions'][:offset]),
                        directory=directory/'alternate',mode=mode,alternate=target)
                value['trajectories'].append(str(directory/'alternate/result.json'))
    value['status']='completed'
    save(directory/'result.json',value)
    from audit import audit_scene
    save(directory/'summary.json',audit_scene(value))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('index',type=int)
    execute(parser.parse_args().index)

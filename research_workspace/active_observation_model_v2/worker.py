"""共享初态、独立动作；成功或非法输出即停止该轨迹。"""
import argparse
from copy import deepcopy
from unittest.mock import patch
from hardstudy import qualify
from hardstudy.intervention import attempt
from am_common import ROOT,verify,save,METHODS,MODEL_METHODS,ALIAS,MAX_ATTEMPTS,SOURCE_TAG
from am_policy import history_entry
from am_decision import decide


def rollout(item,first,*,directory,method):
    directory.mkdir(parents=True,exist_ok=False)
    steps,decisions,history=[deepcopy(first)],[],[]
    used=0
    value=dict(item=item,attempts=steps,decisions=decisions,method=method,
        model=ALIAS if method in MODEL_METHODS else None,test_used=False,training_approved=False,source=SOURCE_TAG)
    while not steps[-1]['success'] and len(steps)<MAX_ATTEMPTS:
        d=decide(steps[-1],item,method=method,used=used,history=history)
        decisions.append(d)
        used+=d['observation']['extra_cost']
        save(directory/'progress.json',value)
        assert not d['service_failure'],str(d['service_failure'])
        if d['selected'] is None:
            break
        index=len(steps)+1
        step=attempt(item,d['selected']['state'],directory=directory/f'attempt_{index}',index=index)
        steps.append(step)
        history.append(history_entry(d['choices'][-1]['context'],d['selected'],step))
    value.update(success=steps[-1]['success'],status='completed',extra_observations=used)
    save(directory/'result.json',value)
    return value


def execute(index):
    scene=verify()['scenes'][index]
    directory=ROOT/'tasks'/scene['id']
    directory.mkdir(parents=True,exist_ok=False)
    with patch.object(qualify,'ROOT',ROOT):
        q=qualify.run(scene)
    value=dict(scene=scene,eligible=q['eligible'],trajectories=[],status='running',
        test_used=False,training_approved=False,source=SOURCE_TAG)
    if q['eligible']:
        item=dict(scene,id=scene['id']+'_qualification',arm='new_rule')
        for method in METHODS:
            rollout(item,q['steps'][1],directory=directory/method,method=method)
            value['trajectories'].append(str(directory/method/'result.json'))
    value['status']='completed'
    save(directory/'result.json',value)
    from am_audit import audit_scene
    save(directory/'summary.json',audit_scene(value))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('index',type=int)
    execute(parser.parse_args().index)

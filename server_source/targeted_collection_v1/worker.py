"""独立进程中执行同前缀反事实分支，严格保留三次轨迹预算。"""
import argparse
from copy import deepcopy
from unittest.mock import patch
from loopstudy.episode import decide
from hardstudy import qualify
from hardstudy.intervention import attempt
from hardstudy.feedback import project_step
from pilot_common import ROOT, verify, save
from policy import alternatives, MAX_ATTEMPTS


def rollout(item, prefix, *, directory, alternate=None):
    directory.mkdir(parents=True, exist_ok=False)
    steps, decisions = deepcopy(prefix)
    override_at = len(steps) if alternate else None
    value = dict(item=item, attempts=steps, decisions=decisions, override_at=override_at,
                 source='expert_counterfactual_rule_continuation', model=None,
                 test_used=False, training_approved=False)
    save(directory/'progress.json', value)
    while not steps[-1]['success'] and len(steps) < MAX_ATTEMPTS:
        choice = decide(item, steps[-1], decisions)
        if len(steps) == override_at:
            assert alternate in choice['candidates']
            choice.update(selected=deepcopy(alternate), source='expert_counterfactual_candidate')
        decisions.append(choice)
        if choice['selected'] is None:
            break
        index = len(steps)+1
        step = attempt(item, choice['selected']['state'], directory=directory/f'attempt_{index}', index=index)
        steps.append(project_step(step, item))
        save(directory/'progress.json', value)
    value.update(success=steps[-1]['success'], status='completed')
    save(directory/'result.json', value)
    return value


def execute(index):
    scene = verify()['scenes'][index]
    directory = ROOT/'tasks'/scene['id']
    assert not directory.exists(), 'Partial task must be diagnosed, never silently retried'
    directory.mkdir(parents=True)
    with patch.object(qualify, 'ROOT', ROOT):
        qualification = qualify.run(scene)
    value = dict(scene=scene, eligible=qualification['eligible'], trajectories=[], nodes=[],
                 status='running', model=None, test_used=False, training_approved=False)
    save(directory/'progress.json', value)
    if qualification['eligible']:
        item = dict(scene, id=scene['id']+'_search', arm='new_rule')
        first = project_step(qualification['steps'][1], item)
        baseline = rollout(item, ([first], []), directory=directory/'baseline')
        value['trajectories'].append(str(directory/'baseline/result.json'))
        for offset, decision in enumerate(baseline['decisions']):
            if decision['selected'] is None:
                continue
            paths = [str(directory/'baseline/result.json')]
            for number, selected in enumerate(alternatives(decision['candidates'], decision['selected'])):
                target = directory/f'node_{offset+1}_alt_{number}'
                rollout(item, (baseline['attempts'][:offset+1], baseline['decisions'][:offset]),
                        directory=target, alternate=selected)
                path = str(target/'result.json')
                paths.append(path)
                value['trajectories'].append(path)
                save(directory/'progress.json', value)
            value['nodes'].append(dict(after_attempt=offset+1, trajectories=paths))
    value['status'] = 'completed'
    save(directory/'result.json', value)
    from audit import audit_scene
    checked = audit_scene(value)
    save(directory/'summary.json', checked)
    save(directory/'progress.json', dict(value, audit=checked))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('index', type=int)
    execute(parser.parse_args().index)

"""独立重建物理、噪声、候选和共享前缀，有限分支不放宽成功判据。"""
from pathlib import Path
from loopstudy import audit as original
from loopstudy.actions import initial, candidates, choose_rule
from hardstudy.qualify import audit as qualify_audit
from hardstudy.audit import clean_step
from hardstudy.feedback import project_step
from hardstudy.intervention import audit as intervention_audit
from hardstudy.bridge import bound
from pilot_common import ROOT, read, MAX_PHYSICAL
from policy import alternatives, MAX_ATTEMPTS


def audit_decision(decision, step, history, *, overridden):
    assert decision['after_attempt'] == step['index']
    assert decision['before'] == step['state'] and decision['feedback'] == step['feedback']
    rows = candidates(step['feedback'], step['state'], history)
    assert rows == decision['candidates'] and decision.get('model') is None
    assert 'event' not in decision
    if not rows:
        assert decision['selected'] is None and decision.get('invalid')
        return
    assert decision['selected'] in rows
    if overridden:
        assert decision['source'] == 'expert_counterfactual_candidate'
    else:
        assert decision['selected'] == choose_rule(rows, step['state'], report=step['feedback'])


def audit_trace(value, reference):
    item, steps, decisions = value['item'], value['attempts'], value['decisions']
    assert value['status'] == 'completed' and value['model'] is None
    assert not value['test_used'] and not value['training_approved']
    assert 1 <= len(steps) <= MAX_ATTEMPTS and len(decisions) <= MAX_ATTEMPTS-1
    state = initial()
    with bound(item):
        for offset, step in enumerate(steps):
            assert step['index'] == offset+1 and step['state'] == state
            intervention_audit(step, item)
            clean = clean_step(step, item)
            assert step == project_step(clean, item)
            original.physical(clean, item, reference)
            if offset < len(decisions):
                assert not step['success']
                decision = decisions[offset]
                audit_decision(decision, step, decisions[:offset],
                               overridden=step['index'] == value['override_at'])
                state = decision['selected']['state'] if decision['selected'] else None
    assert value['success'] == steps[-1]['success']
    assert not any(step['success'] for step in steps[:-1])
    if state is None:
        assert len(decisions) == len(steps) and not value['success']
    else:
        assert len(decisions) == len(steps)-1
        assert value['success'] or len(steps) == MAX_ATTEMPTS


def check_branches(value, baseline, reference):
    expected_paths = [str(ROOT/'tasks'/value['scene']['id']/'baseline/result.json')]
    nodes = []
    for offset, decision in enumerate(baseline['decisions']):
        if decision['selected'] is None:
            continue
        paths = [expected_paths[0]]
        for number, selected in enumerate(alternatives(decision['candidates'], decision['selected'])):
            path = ROOT/'tasks'/value['scene']['id']/f'node_{offset+1}_alt_{number}/result.json'
            branch = read(path)
            assert branch['item'] == baseline['item'] and branch['override_at'] == offset+1
            assert branch['attempts'][:offset+1] == baseline['attempts'][:offset+1]
            assert branch['decisions'][:offset] == baseline['decisions'][:offset]
            assert branch['decisions'][offset]['selected'] == selected
            audit_trace(branch, reference)
            paths.append(str(path))
            expected_paths.append(str(path))
        nodes.append(dict(after_attempt=offset+1, trajectories=paths))
    assert value['nodes'] == nodes and value['trajectories'] == expected_paths


def audit_scene(value):
    scene = value['scene']
    q = read(ROOT/'qualification'/scene['id']/'result.json')
    qualify_audit(q, scene)
    assert value['status'] == 'completed' and value['eligible'] == q['eligible']
    assert value['model'] is None and not value['test_used'] and not value['training_approved']
    paths = {step['result_path'] for step in q['steps']}
    success = None
    if q['eligible']:
        expected_item = dict(scene, id=scene['id']+'_search', arm='new_rule')
        baseline = read(ROOT/'tasks'/scene['id']/'baseline/result.json')
        assert baseline['item'] == expected_item and baseline['override_at'] is None
        assert baseline['attempts'][0] == project_step(q['steps'][1], expected_item)
        reference = read(Path(q['steps'][0]['result_path']))['records'][0]
        audit_trace(baseline, reference)
        check_branches(value, baseline, reference)
        for filename in value['trajectories']:
            paths.update(step['result_path'] for step in read(filename)['attempts'])
        success = baseline['success']
    else:
        assert not value['trajectories'] and not value['nodes']
    disk = set(ROOT.joinpath('tasks', scene['id']).glob('**/attempt_*/result.json'))
    disk.update(ROOT.joinpath('qualification', scene['id']).glob('[01]/result.json'))
    assert {str(p) for p in disk} == paths
    assert len(paths) <= MAX_PHYSICAL
    return dict(id=scene['id'], passed=True, eligible=q['eligible'], qualification=q['status'],
                physical_executions=len(paths), baseline_success=success,
                trajectories=len(value['trajectories']), decision_nodes=len(value['nodes']),
                training_approved=False, test_used=False, model_calls=0)

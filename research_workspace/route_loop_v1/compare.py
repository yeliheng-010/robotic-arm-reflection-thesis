"""跨方法相同状态的物理复现，以及已知锚点和候选集合配对。"""
import json
from pathlib import Path
import numpy as np
from bounded.candidates import digest
from loopstudy.actions import PROFILES
from loopstudy.design import ROOT,ANCHOR_SEED
from loopstudy.protocol import verify
from stability.collection_status import atomic


def outcome_equal(expected,actual):
    assert expected['accepted']==actual['accepted']
    assert expected['physical_success']==actual['physical_success']
    before,after = expected.get('error'),actual.get('error')
    assert (before or {}).get('error_type')==(after or {}).get('error_type')
    if before:
        assert before['evidence']['motion_context']['phase']==after['evidence']['motion_context']['phase']
    np.testing.assert_allclose(expected['evaluation']['position'],actual['evaluation']['position'],atol=1e-8,rtol=0)


def reference(item,state):
    if item['seed']!=ANCHOR_SEED:
        return None
    yaw = PROFILES[state['profile']]
    variant = f'yaw_{yaw}' if yaw else 'default' if state['parameters']['lift_height']==.35 else 'lift45'
    root = 'descent_route_v1' if yaw else 'feedback_semantics_v2'
    path = ROOT.parent/root/'physical/tasks'/f"{item['scene_id']}_{variant}/result.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text())['records'][0]
    return value if value['parameters']==state['parameters'] else None


def compare_physics(results):
    known,same,anchors = {},0,0
    for result in results:
        item=result['item']
        for step in result['attempts']:
            record=json.loads(Path(step['result_path']).read_text())['records'][0]
            key=(item['scene_id'],digest(step['state']))
            if key in known:
                outcome_equal(known[key],record)
                same+=1
            else:
                known[key]=record
            old=reference(item,step['state'])
            if old is not None:
                outcome_equal(old,record)
                anchors+=1
    return dict(shared_state_outcome_checks=same,old_anchor_outcome_checks=anchors)


def compare_candidates(results):
    known,paired,diverged={},0,0
    for result in results:
        if result['item']['arm'] not in ('new_rule','hybrid'):
            continue
        for decision in result['decisions']:
            key=(result['item']['scene_id'],decision['after_attempt'])
            if key not in known:
                known[key]=decision
                continue
            other=known[key]
            if other['before']==decision['before'] and other['feedback']==decision['feedback']:
                assert other['candidates']==decision['candidates']
                paired+=1
            else:
                diverged+=1
    return dict(paired_candidate_sets=paired,diverged_inputs=diverged)


if __name__=='__main__':
    protocol=verify()
    paths=[ROOT/'tasks'/i['id']/'result.json' for i in protocol['items']]
    values=[json.loads(p.read_text()) for p in paths if p.exists()]
    output=dict(passed=True,tasks=len(values),**compare_physics(values),**compare_candidates(values))
    atomic(ROOT/'comparison.json',output)
    print(json.dumps(output))

"""只重建审计过的紧邻成功决策；不生成任何新增监督解释。"""
import json
from pathlib import Path
from curation import input_digest
from loopstudy.selection import messages
from semanticfix2.protocol import sha

SPLITS = {'train_candidate':'train', 'development_validation':'dev'}
SOURCES = {'new_rule':'rule', 'hybrid':'hybrid'}


def split_for(batch, item):
    return 'legacy_dev' if batch=='noisy_loop_v1' else SPLITS[item['split']]


def transition(result, offset, *, batch, root):
    item = result['item']
    decision = result['decisions'][offset]
    steps = result['attempts']
    selected = decision['selected']
    if selected is None or offset+1 >= len(steps) or not steps[offset+1]['success']:
        return None
    assert not steps[offset]['success']
    assert selected['state'] == steps[offset+1]['state']
    prompt = messages(decision['feedback'], decision['before'],
                      rows=decision['candidates'], history=result['decisions'][:offset])
    if item['arm']=='hybrid':
        assert prompt == decision['event']['request']['messages']
    target = selected['id']
    assert sum(c['id']==target for c in decision['candidates'])==1
    target_message = dict(role='assistant', content=json.dumps({'action_id':target}))
    return dict(uid=f"{batch}:{item['id']}:{offset+1}", batch=batch, task_id=item['id'],
                scene_id=item['scene_id'], seed=item['seed'], factor=item['factor'],
                source=SOURCES[item['arm']], source_detail=decision['source'],
                split=split_for(batch,item), input_hash=input_digest(prompt), target=target,
                messages=prompt+[target_message], before_attempt=offset+1, after_attempt=offset+2,
                before_sha256=steps[offset]['result_sha256'],
                after_sha256=steps[offset+1]['result_sha256'],
                result_path=str(root/'tasks'/item['id']/'result.json'),
                result_sha256=sha(root/'tasks'/item['id']/'result.json'),
                model_alias=decision.get('event',{}).get('request',{}).get('model'),
                explanation_source='deterministic_action_template', training_approved=False)


def transitions(results, *, batch, root):
    records = []
    for result in results:
        for offset in range(len(result['decisions'])):
            row = transition(result, offset, batch=batch, root=root)
            if row:
                records.append(row)
    old = json.loads((root/'transitions.json').read_text())['rows']
    index = {(r['task_id'],r['before_attempt']):r for r in old}
    assert len(records)==len(index)==len(old)
    for row in records:
        reference = index[(row['task_id'],row['before_attempt'])]
        assert row['target']==reference['selected']['id']
        assert all(row[k]==reference[k] for k in ('before_sha256','after_sha256','after_attempt'))
    return records

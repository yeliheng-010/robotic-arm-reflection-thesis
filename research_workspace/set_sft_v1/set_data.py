"""保留全部成功动作、训练来源和既有开发诊断口径，无截断编码。"""
import json
from collections import defaultdict
from curation import input_digest
from stability.sft_model import tokenizer
from stability.sft_data import encode
from loss import supervised_start
from set_common import ROOT, OLD, REVIEW, DATA, MODEL, lines, read, save, reviewed_sources


def original(split):
    rows = lines(DATA/(split+'_combined.jsonl'))
    indices = lines(DATA/(split+'_combined.jsonl.index.jsonl'))
    assert len(rows) == len(indices)
    output = []
    for offset, (row, index) in enumerate(zip(rows, indices)):
        target = json.loads(row['messages'][-1]['content'])['action_id']
        assert input_digest(row['messages'][:-1]) == index['input_hash']
        output.append(dict(id=index['input_hash'], messages=row['messages'][:-1],
            accepted_action_ids=[target], groups=index['groups'], sources=index['sources'],
            semantics='immediate_success', diagnostic_index=offset, diagnostic_target=target))
    return output


def training():
    old = original('train')
    fresh = lines(REVIEW/'output_v1/positive_sets.jsonl')
    new = [dict(id=r['id'], messages=r['messages'], accepted_action_ids=r['accepted_action_ids'],
        groups=[r['group']], sources=[r['source']], semantics=r['label_semantics'],
        success_timing=r['success_timing']) for r in fresh]
    rows = old+new
    assert len(old) == 159 and len(new) == 30
    assert len({r['id'] for r in rows}) == len(rows) == 189
    assert sum(len(r['accepted_action_ids']) for r in rows) == 197
    return rows, new


def development(split):
    selected = {r['id']:r for r in original(split)}
    grouped = defaultdict(list)
    for row in lines(DATA/'provenance.jsonl'):
        if row['split'] == split:
            grouped[row['input_hash']].append(row)
    output = []
    for key, members in sorted(grouped.items()):
        prompt = members[0]['messages'][:-1]
        assert all(r['messages'][:-1] == prompt for r in members)
        item = dict(id=key, messages=prompt, accepted_action_ids=sorted({r['target'] for r in members}),
                    split=split, groups=sorted({f"{r['batch']}:{r['seed']}" for r in members}),
                    semantics='observed_immediate_success_set', diagnostic_index=None, diagnostic_target=None)
        if key in selected:
            prior = selected[key]
            assert prior['messages'] == prompt
            item.update(diagnostic_index=prior['diagnostic_index'], diagnostic_target=prior['diagnostic_target'])
        output.append(item)
    assert set(selected) <= set(grouped)
    return output


def encoded_group(tok, group):
    assert input_digest(group['messages']) == group['id']
    candidates = json.loads(group['messages'][1]['content'])['candidates']
    ids = [c['id'] for c in candidates]
    targets = group['accepted_action_ids']
    assert len(targets) == len(set(targets)) and targets
    assert all(ids.count(target) == 1 for target in targets)
    variants = []
    for target in targets:
        answer = dict(role='assistant', content=json.dumps({'action_id':target}))
        row = encode(tok, group['messages']+[answer], max_length=262144)
        start = supervised_start(row)
        assert all(v == -100 for v in row['labels'][:start])
        variants.append(row)
    prompts = [r['input_ids'][:supervised_start(r)] for r in variants]
    assert all(p == prompts[0] for p in prompts)
    return dict(id=group['id'], variants=variants, accepted_action_ids=targets)


def preflight():
    reviewed_sources()
    train, fresh = training()
    development_rows = {split:development(split) for split in ('dev', 'legacy_dev')}
    evaluation = [r for rows in development_rows.values() for r in rows]
    evaluation += [dict(r, split='train_diagnostic', diagnostic_index=None, diagnostic_target=None) for r in fresh]
    assert len(development_rows['dev']) == 55 and len(development_rows['legacy_dev']) == 63
    train_ids = {r['id'] for r in train}
    assert not train_ids & {r['id'] for rows in development_rows.values() for r in rows}
    assert not {g for r in train for g in r['groups']} & {g for rows in development_rows.values() for r in rows for g in r['groups']}
    tok = tokenizer(str(MODEL))
    summary = dict(splits={}, no_truncation=True, assistant_only=True, test_used=False)
    for name, rows in (('train', train), ('eval', evaluation)):
        encoded = [encoded_group(tok, row) for row in rows]
        lengths = [len(v['input_ids']) for r in encoded for v in r['variants']]
        summary['splits'][name] = dict(inputs=len(rows), responses=len(lengths), max_tokens=max(lengths),
            min_tokens=min(lengths), multi_inputs=sum(len(r['variants']) > 1 for r in encoded))
        save(ROOT/(name+'.json'), rows)
        save(ROOT/(name+'_encoded.json'), encoded)
    assert read(ROOT/'train_encoded.json')[:159] == [dict(id=r['id'], variants=[e],
        accepted_action_ids=r['accepted_action_ids']) for r,e in zip(train[:159],read(OLD/'train_encoded.json'))]
    save(ROOT/'data_preflight.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    preflight()

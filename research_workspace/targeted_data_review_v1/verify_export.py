"""从原始节点独立核对导出视图，不依赖prepare的分类实现。"""
import json
from collections import Counter
from pathlib import Path
from curation import input_digest
from common import sha


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def verify_record(row, raw):
    assert row['id'] == input_digest(raw['messages']) == raw['input_hash']
    assert row['messages'] == raw['messages'] and row['tested_outcomes'] == raw['tested_outcomes']
    positive = {o['action_id'] for o in raw['tested_outcomes'] if o['terminal_success']}
    negative = {o['action_id'] for o in raw['tested_outcomes'] if not o['terminal_success']}
    candidates = {c['id'] for c in json.loads(raw['messages'][1]['content'])['candidates']}
    assert set(row['accepted_action_ids']) == positive and set(row['observed_unsuccessful_action_ids']) == negative
    assert set(row['untested_action_ids']) == candidates-positive-negative
    assert len(row['accepted_action_ids']) == len(positive)
    assert row['source'] == raw['source'] and row['model'] is None
    assert row['group'] == f"targeted_collection_v1:{raw['seed']}"
    assert row['remaining_attempts'] == 3-raw['after_attempt']
    assert not row['test_used'] and not row['training_approved']
    assert row['scene_id'] == raw['scene_id'] and row['after_attempt'] == raw['after_attempt']
    assert row['label_semantics'] == raw['label_semantics'] and row['split'] == 'train_candidate'
    timings = {o['immediate_success'] for o in raw['tested_outcomes'] if o['terminal_success']}
    expected = 'mixed' if len(timings) == 2 else 'immediate' if True in timings else 'delayed' if timings else 'none'
    assert row['success_timing'] == expected


def verify(directory, raw_rows, *, held, old_train):
    raw = {r['input_hash']: r for r in raw_rows}
    assert len(raw) == len(raw_rows)
    files = {name: read_lines(directory/(name+'.jsonl')) for name in
             ('positive_sets', 'single_success', 'multi_success', 'unresolved', 'quarantine')}
    ids = [r['id'] for k in ('single_success', 'multi_success', 'unresolved') for r in files[k]]
    ids += [r['record']['id'] for r in files['quarantine']]
    assert len(ids) == len(set(ids)) == len(raw) and set(ids) == set(raw)
    for name in ('positive_sets', 'single_success', 'multi_success', 'unresolved'):
        for row in files[name]:
            verify_record(row, raw[row['id']])
            assert row['id'] not in held | old_train
            count = len(row['accepted_action_ids'])
            assert (count == 1 if name == 'single_success' else count > 1 if name == 'multi_success'
                    else count == 0 if name == 'unresolved' else count > 0)
    for row in files['quarantine']:
        verify_record(row['record'], raw[row['record']['id']])
        assert row['record']['id'] in held | old_train
    positives = files['single_success']+files['multi_success']
    assert {r['id']:r for r in positives} == {r['id']:r for r in files['positive_sets']}
    singles = files['single_success']
    sft = read_lines(directory/'single_success_sft.jsonl')
    assert len(sft) == len(singles)
    for data, row in zip(sft, singles):
        assert set(data) == {'messages'} and data['messages'][:-1] == row['messages']
        answer = data['messages'][-1]
        assert answer['role'] == 'assistant'
        assert json.loads(answer['content']) == {'action_id':row['accepted_action_ids'][0]}
    assert read_lines(directory/'provenance.jsonl') == raw_rows
    return dict(passed=True, inputs=len(raw), positive_inputs=len(positives),
        successful_action_observations=sum(len(r['accepted_action_ids']) for r in positives),
        counts={k:len(v) for k,v in files.items()}, single_sft_rows=len(sft),
        single_timing=dict(Counter(r['success_timing'] for r in singles)),
        positive_groups=sorted({r['group'] for r in positives}),
        training_started=False, test_used=False)


def verify_manifest(root):
    manifest = json.loads((root/'manifest.json').read_text())
    for section in ('code', 'inputs', 'artifacts'):
        for path, expected in manifest[section].items():
            assert sha(Path(path)) == expected, f'Changed {section}: {path}'
    return True

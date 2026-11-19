"""正式导出的输入/图像/动作身份及全量编码检查，不进行模型训练。"""
import json
import os
import re
from pathlib import Path
from transformers import AutoProcessor
from collection_common import read, save, sha, verify
from check_input import public
from sv_strategy_actions import check
from encoding import encode
from rc_gate import summarize, assess

ROOT = Path(__file__).resolve().parent
MODEL = ROOT.parent/'qwen35/models/Qwen3.5-4B'


def lines(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def validate_record(row, *, split, processor):
    assert row['split'] == split and row['label_scope'] == 'one_verified_option_not_unique_optimum'
    assert sha(row['source_input']) == row['source_sha256']
    source = read(row['source_input'])
    public(source['request'])
    assert row['image_sha256'] == source['visual']['sha256']
    assert all(sha(p) == h for p, h in zip(source['visual']['paths'], row['image_sha256']))
    system, user, assistant = row['messages']
    assert system == source['direct_messages'][0] and user['role'] == 'user'
    content = user['content']
    assert len(content) == 3 and [c['type'] for c in content] == ['image', 'image', 'text']
    assert [c['image'] for c in content[:2]] == source['visual']['paths']
    assert content[2]['text'] == source['direct_messages'][1]['content']
    assert json.loads(content[2]['text']) == source['request']
    assert assistant['role'] == 'assistant' and json.loads(assistant['content']) == dict(action=row['action'])
    assert row['action'] in row['accepted_actions']
    for action in row['accepted_actions']:
        check(action, source['request'])
    facts = next(e['value'] for e in source['request']['evidence'] if e['field'] == 'execution_facts')
    assert facts['task_completed'] is (row['kind'] == 'completed_stop')
    _, stats = encode(processor, row['messages'])
    return dict(input_id=row['input_id'], snapshot_id=row['snapshot_id'], seed=row['seed'],
        split=split, kind=row['kind'], stats=stats)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    export_job = os.environ['RECOVERY_EXPORT_JOB']
    assert re.fullmatch(r'\d+', export_job)
    source = ROOT.parent/'recovery_dataset_v1/exports'/('job_'+export_job)
    manifest = verify(source/'manifest.json')
    assert all(sha(source/p) == h for p, h in manifest['outputs'].items())
    outcomes = lines(source/'outcomes.jsonl')
    assert summarize(outcomes) == manifest['summary'] and assess(manifest['summary']) == manifest['gate']
    processor = AutoProcessor.from_pretrained(str(MODEL), local_files_only=True,
        trust_remote_code=False, min_pixels=128*128, max_pixels=448*448)
    result, groups, inputs = [], {}, {}
    for split in ('train', 'dev'):
        rows = lines(source/(split+'.jsonl'))
        assert len(rows) == manifest['counts'][split]['records']
        for row in rows:
            assert groups.setdefault(row['seed'], split) == split
            assert row['input_id'] not in inputs
            inputs[row['input_id']] = split
            result.append(validate_record(row, split=split, processor=processor))
    output = ROOT/'results'/('job_'+os.environ['SLURM_JOB_ID']+'.json')
    identities = {str(p): sha(p) for p in (Path(__file__), source/'manifest.json',
        ROOT.parent/'visual_sft_v1/encoding.py')}
    save(output, dict(passed=True, records=result, source=str(source/'manifest.json'),
        quantitative_ready=manifest['gate']['quantitative_ready'], training_ready=False,
        training_updates=0, model_generations=0, identities=identities))
    print(dict(passed=True, records=len(result), counts=manifest['counts'],
        max_prompt_tokens=max((r['stats']['prompt_tokens'] for r in result), default=0)), flush=True)


if __name__ == '__main__':
    main()

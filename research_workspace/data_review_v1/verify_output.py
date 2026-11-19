"""独立读取导出文件、索引与清单，复核标签和来源守恒。"""
import hashlib
import json
from collections import Counter
from pathlib import Path
from curation import input_digest

HERE = Path(__file__).resolve().parent
OUTPUT = HERE/'output_v1'
VISIBLE_KEYS = {'error','state','candidates','history','executor_profiles'}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def validate_messages(messages, target):
    assert [m['role'] for m in messages]==['system','user','assistant']
    assert all(set(m)=={'role','content'} for m in messages)
    visible = json.loads(messages[1]['content'])
    assert set(visible)==VISIBLE_KEYS
    assert json.loads(messages[-1]['content'])=={'action_id':target}
    assert sum(c['id']==target for c in visible['candidates'])==1


def verify_file(name, *, source_rows, expected):
    data = lines(OUTPUT/name)
    index = lines(OUTPUT/(name+'.index.jsonl'))
    assert len(data)==len(index)==expected
    split, source = name[:-6].rsplit('_',1)
    for value, row in zip(data,index):
        assert set(value)=={'messages'} and row['split']==split
        validate_messages(value['messages'], row['target'])
        assert input_digest(value['messages'][:-1])==row['input_hash']
        members = [source_rows[uid] for uid in row['members']]
        assert {m['source'] for m in members}==set(row['sources'])
        assert {f"{m['batch']}:{m['seed']}" for m in members}==set(row['groups'])
        assert all(m['split']==split and m['target']==row['target'] for m in members)
        assert all(m['input_hash']==row['input_hash'] for m in members)
        assert value['messages'] in [m['messages'] for m in members]
        assert source=='combined' or source in row['sources']
    return index


def main():
    manifest = json.loads((OUTPUT/'manifest.json').read_text())
    for name, expected in manifest['code'].items():
        assert file_hash(HERE/name)==expected, name
    for name, expected in manifest['artifacts'].items():
        assert file_hash(OUTPUT/name)==expected, name
    summary = json.loads((OUTPUT/'summary.json').read_text())
    records = lines(OUTPUT/'provenance.jsonl')
    sources = {r['uid']:r for r in records}
    assert len(sources)==len(records)==summary['raw_transitions']
    combined = []
    for name, count in summary['exports'].items():
        index = verify_file(name,source_rows=sources,expected=count)
        if name.endswith('_combined.jsonl'):
            combined.extend(index)
    used = [uid for r in combined for uid in r['members']]
    used += [r['uid'] for r in lines(OUTPUT/'quarantine.jsonl')]
    assert Counter(used)==Counter(sources.keys())
    train = {r['input_hash'] for r in combined if r['split']=='train'}
    dev = {r['input_hash'] for r in combined if r['split']!='train'}
    assert not train & dev
    evidence = dict(passed=True,checked_files=len(summary['exports']),
                    raw_records=len(records),train_eval_overlap=0,
                    source_membership_conserved=True,manifest_sha256=file_hash(OUTPUT/'manifest.json'),
                    verifier_sha256=file_hash(Path(__file__)))
    (HERE/'output_verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__=='__main__':
    main()

"""读取已审核数据，按真实tokenizer编码，不裁剪或更改来源。"""
import hashlib
import json
from pathlib import Path
from stability.sft_data import encode
from stability.sft_model import tokenizer
from loss import supervised_start

ROOT = Path('/home/yeliheng/grasp_server/candidate_sft_v2')
DATA = ROOT.parent/'data_review_v1/output_v1'
MODEL = ROOT.parent/'qwen35/models/Qwen3.5-4B'
SPLITS = {'train':159,'dev':49,'legacy_dev':29}


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path,value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)


def load_split(split):
    assert split in SPLITS, 'Only declared development splits; final test is sealed'
    manifest = read(DATA/'manifest.json')
    name = split+'_combined.jsonl'
    index = name+'.index.jsonl'
    for filename in (name,index):
        assert sha(DATA/filename)==manifest['artifacts'][filename]
    rows = [json.loads(line) for line in (DATA/name).read_text().splitlines()]
    indices = [json.loads(line) for line in (DATA/index).read_text().splitlines()]
    assert len(rows)==len(indices)==SPLITS[split]
    assert all(r['split']==split for r in indices)
    assert len({r['input_hash'] for r in indices})==len(indices)
    return rows,indices


def preflight():
    tok = tokenizer(str(MODEL))
    result = dict(model=str(MODEL),model_type=read(MODEL/'config.json')['model_type'],
                  dataset_manifest_sha256=sha(DATA/'manifest.json'),splits={})
    inputs = {}
    for split in SPLITS:
        rows,index = load_split(split)
        encoded = [encode(tok,r['messages'],max_length=262144) for r in rows]
        starts = [supervised_start(r) for r in encoded]
        lengths = [len(r['input_ids']) for r in encoded]
        assert all(set(r['labels'][:start])=={-100} for r,start in zip(encoded,starts))
        assert all(json.loads(r['messages'][-1]['content'])=={'action_id':m['target']}
                   for r,m in zip(rows,index))
        save(ROOT/f'{split}_encoded.json',encoded)
        inputs[split] = {r['input_hash'] for r in index}
        result['splits'][split] = dict(n=len(rows),min=min(lengths),max=max(lengths),
            median=sorted(lengths)[len(lengths)//2],longest_index=lengths.index(max(lengths)),
            answer_tokens=sorted({len(r['labels'])-s for r,s in zip(encoded,starts)}),
            no_truncation=True,assistant_only_mask=True)
    assert not inputs['train'] & (inputs['dev']|inputs['legacy_dev'])
    save(ROOT/'data_preflight.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    preflight()

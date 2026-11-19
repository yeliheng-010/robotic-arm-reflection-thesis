import json
import os
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'candidate_sft_v2'))
import runtime
assert runtime.__file__.endswith('/candidate_sft_v2/runtime.py')
assert sys.modules['loss'].__file__.endswith('/candidate_sft_v2/loss.py')
from f_common import read, save, sha
from transformers import AutoProcessor
from encoding import encode


def job(name):
    value = os.environ[name]
    assert re.fullmatch(r'\d+', value)
    return value


def verify(path):
    value = read(path)
    assert all(sha(p) == h for p, h in value['identities'].items())
    return value


def config():
    assert os.environ.get('SLURM_JOB_ID')
    value = verify(ROOT/'manifest.json')
    assert value['training_authorized'] and value['epochs'] == 1
    assert value['rank'] == 8 and value['accumulation'] == 4
    return value


def rows(config):
    source = Path(config['dataset'])/'train.jsonl'
    assert sha(source) == config['identities'][str(source)]
    with source.open(encoding='utf-8') as stream:
        result = [json.loads(line) for line in stream if line.strip()]
    assert len(result) == config['train_samples']
    assert all(row['split'] == 'train' for row in result)
    return result


def processor(config):
    return AutoProcessor.from_pretrained(config['model'], local_files_only=True,
        trust_remote_code=False, min_pixels=128*128, max_pixels=448*448)


def encoded(row, proc):
    assert sha(row['source_input']) == row['source_sha256']
    paths = [c['image'] for c in row['messages'][1]['content'] if c['type'] == 'image']
    assert len(paths) == len(row['image_sha256']) == 2
    assert all(sha(p) == h for p, h in zip(paths, row['image_sha256']))
    return encode(proc, row['messages'])[0]

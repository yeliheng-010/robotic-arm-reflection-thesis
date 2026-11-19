"""冻结探索性试训配置、代码、基础模型与不截断的token预检。"""
import hashlib
import json
from pathlib import Path
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.sft_data import encode, read_split

MODEL = Path('/home/yeliheng/grasp_server/qwen35/models/Qwen3.5-4B')
FILES = ('sft_data.py', 'sft_model.py', 'sft_evaluate.py', 'sft_train.py', 'sft_freeze.py',
         'collection_status.py')


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def code_hashes():
    return {name: file_hash(OUT/'stability'/name) for name in FILES}


def preflight(dataset, tokenizer):
    stats, keys = {}, set()
    for split in ('train', 'validation'):
        rows = read_split(dataset, split)
        prompts = {r['metadata']['prompt_sha256'] for r in rows}
        assert not keys.intersection(prompts), 'Train-validation leakage'
        keys.update(prompts)
        encoded = [encode(tokenizer, r['messages'], max_length=4096) for r in rows]
        lengths = [len(r['input_ids']) for r in encoded]
        stats[split] = {'samples': len(rows), 'max_tokens': max(lengths), 'min_tokens': min(lengths),
                        'mean_tokens': sum(lengths)/len(lengths), 'truncated': 0}
    return stats


def main():
    from stability.sft_model import tokenizer
    dataset, output = OUT/'pilot_sft_data_v1', OUT/'pilot_sft_v1'
    assert not output.exists(), 'Preserve existing training output'
    stats = preflight(dataset, tokenizer(MODEL))
    config = {'purpose': 'preliminary_rule_expert_qlora_not_final_experiment',
        'model': str(MODEL), 'dataset': str(dataset), 'epochs': 1, 'seed': 42,
        'rank': 8, 'learning_rate': 1e-4, 'accumulation': 8, 'max_length': 4096,
        'amp_init_scale': 256, 'test_used': False, 'preflight': stats,
        'dataset_manifest_sha256': file_hash(dataset/'manifest.json'), 'code': code_hashes(),
        'model_files': {p.name: file_hash(p) for p in MODEL.iterdir() if p.is_file()}}
    output.mkdir()
    atomic(output/'manifest.json', config)
    print(json.dumps({'output': str(output), 'preflight': stats, 'epochs': 1}), flush=True)


if __name__ == '__main__':
    main()

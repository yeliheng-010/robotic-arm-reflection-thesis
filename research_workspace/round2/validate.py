"""在冻结validation上分片比较基础模型与保存后的adapter。"""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import time
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.sft_data import encode, read_split
from stability.sft_freeze import file_hash, code_hashes
from stability.sft_model import device_setup, load_model, tokenizer
from stability.sft_validate import generate, manual_loss

RUN = OUT/'round2_sft_v1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', choices=('base', 'adapted'), required=True)
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--shards', type=int, default=2)
    args = parser.parse_args()
    assert 0 <= args.shard < args.shards
    config = json.loads((RUN/'manifest.json').read_text())
    assert config['code'] == code_hashes()
    for path, expected in config['source_identity'].items():
        assert file_hash(Path(path)) == expected
    target = RUN/f'validation_{args.arm}_{args.shard}.json'
    assert not target.exists(), 'Preserve existing generation results'
    environment = device_setup(config['seed'])
    tok, (model, _) = tokenizer(config['model']), load_model(config)
    adapter_hash = None
    if args.arm == 'adapted':
        trained = json.loads((RUN/'result.json').read_text())
        assert trained['status'] == 'completed'
        adapter_hash = file_hash(RUN/'adapter/adapter_model.safetensors')
        assert adapter_hash == trained['adapter_files']['adapter_model.safetensors']
        model.load_adapter(RUN/'adapter', adapter_name='expanded', is_trainable=False)
        model.set_adapter('expanded')
    model.eval()
    model.requires_grad_(False)
    rows = read_split(Path(config['dataset']), 'validation')
    selected = list(range(args.shard, len(rows), args.shards))
    result = dict(status='running', arm=args.arm, shard=args.shard, shards=args.shards,
        environment=environment, test_used=False, physics_evaluated=False, results=[],
        dataset_manifest_sha256=config['dataset_manifest_sha256'], adapter_sha256=adapter_hash,
        started_at=time.time(), total=len(selected))
    with model.disable_adapter() if args.arm == 'base' else nullcontext():
        result['manual_loss_check'] = manual_loss(model, encode(tok, rows[selected[0]]['messages'], max_length=4096))
        for index in selected:
            result['results'].append(dict(index=index, **generate(model, tok, rows[index])))
            atomic(target, result)
            print(json.dumps({'arm': args.arm, 'shard': args.shard,
                'completed': len(result['results']), 'total': len(selected)}), flush=True)
    result.update(status='completed', ended_at=time.time(), samples=len(selected),
        json_with_changes=sum(r['json_with_changes'] for r in result['results']),
        changes_exact_match=sum(r['changes_exact_match'] for r in result['results']))
    atomic(target, result)


if __name__ == '__main__':
    main()

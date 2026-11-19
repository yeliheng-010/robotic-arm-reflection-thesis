"""基础、原159模型和新189模型共享成功集合和确定性生成配置。"""
import argparse
import json
import os
import time
import traceback
import torch
from smoke import probe
from set_common import ROOT, OLD, SHARDS, read, save, sha, verify
from set_runtime import setup, predict


def load(mode, config):
    owner = ROOT if mode == 'after' else OLD
    trained = read(owner/'training/result.json')
    assert trained['status'] == 'completed'
    adapter = owner/'training/adapter'
    assert all(sha(adapter/n) == h for n,h in trained['adapter_files'].items())
    if mode == 'after':
        assert trained['manifest_sha256'] == sha(ROOT/'manifest.json')
    model, _, tok, environment = setup(config, adapter=adapter)
    probe_row = read(ROOT/'eval_encoded.json')[0]['variants'][0] if mode == 'after' else read(OLD/'dev_encoded.json')[0]
    expected = torch.load(owner/'training/reference_logits.pt', weights_only=True)
    error = float((expected-probe(model, probe_row)).abs().max())
    assert error <= 1e-4, f'Adapter reload mismatch: {error}'
    return model, tok, environment, error


def evaluate(mode, shard):
    config = verify()
    output = ROOT/'evaluation'/mode/f'shard_{shard}'
    output.mkdir(parents=True, exist_ok=False)
    save(output/'progress.json', dict(status='loading', job=os.environ['SLURM_JOB_ID']))
    try:
        model, tok, environment, error = load(mode, config)
        raw, encoded = read(ROOT/'eval.json'), read(ROOT/'eval_encoded.json')
        rows, started = [], time.monotonic()
        for index in range(shard, len(raw), SHARDS):
            for method in (('new189',) if mode == 'after' else ('base', 'previous159')):
                result = predict(model, tok, encoded[index], raw=raw[index], baseline=method == 'base')
                result.update(index=index, id=raw[index]['id'], split=raw[index]['split'], method=method,
                    diagnostic_index=raw[index]['diagnostic_index'], diagnostic_target=raw[index]['diagnostic_target'])
                rows.append(result)
                save(output/'progress.json', dict(status='running', completed=len(rows),
                    expected=len(range(shard, len(raw), SHARDS))*(1 if mode == 'after' else 2),
                    rows=rows, elapsed_s=time.monotonic()-started))
                print(json.dumps(dict(method=method, index=index, split=result['split'],
                    valid=result['candidate_valid'], set_match=result['set_match'])), flush=True)
        save(output/'result.json', dict(status='completed', rows=rows, shard=shard,
            environment=environment, reload_error=error, elapsed_s=time.monotonic()-started,
            manifest_sha256=sha(ROOT/'manifest.json'), test_used=False))
        save(output/'progress.json', dict(status='completed', completed=len(rows)))
    except BaseException as error:
        save(output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['before', 'after'])
    parser.add_argument('--shard', type=int, required=True, choices=range(SHARDS))
    args = parser.parse_args()
    evaluate(args.mode, args.shard)

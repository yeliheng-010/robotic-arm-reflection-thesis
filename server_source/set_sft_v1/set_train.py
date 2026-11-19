"""189个逻辑输入独立一轮训练，逐回复反传但按输入聚合更新。"""
import json
import os
import time
import traceback
import torch
from stability.sft_data import epoch_groups
from train import checkpoint
from smoke import probe
from set_common import ROOT, read, save, sha, verify
from set_runtime import setup, optimizer_step


def epoch(model, params, tok, *, config, output):
    rows = read(ROOT/'train_encoded.json')
    order = epoch_groups(len(rows), accumulation=config['accumulation'], seed=config['seed'])
    assert len(order) == 24 and len(order[-1]) == 5
    save(output/'epoch_order.json', order)
    optimizer = torch.optim.AdamW(params.values(), lr=config['learning_rate'])
    scaler = torch.amp.GradScaler('cuda', init_scale=config['amp_init_scale'])
    updates, started = [], time.monotonic()
    for step, indices in enumerate(order, 1):
        value = optimizer_step(model, params, groups=[rows[i] for i in indices], optimizer=optimizer, scaler=scaler)
        value.update(step=step, total_steps=len(order), indices=indices,
            elapsed_s=time.monotonic()-started, peak_allocated_bytes=torch.cuda.max_memory_allocated())
        updates.append(value)
        save(output/'updates.json', updates)
        save(output/'progress.json', dict(phase='training', last_update=value))
        print(json.dumps(value), flush=True)
        if step % 6 == 0 or step == len(order):
            checkpoint(model, tok, output=output, step=step, optimizer=optimizer, scaler=scaler)
    assert sorted(i for u in updates for i in u['indices']) == list(range(189))
    assert sum(u['responses'] for u in updates) == 197
    return updates


def main():
    config = verify()
    smoke = read(ROOT/'smoke/passed.json')
    assert smoke['passed'] and smoke['manifest_sha256'] == sha(ROOT/'manifest.json')
    output = ROOT/'training'
    output.mkdir(exist_ok=False)
    save(output/'progress.json', dict(phase='loading', job=os.environ['SLURM_JOB_ID']))
    try:
        model, params, tok, environment = setup(config)
        original = {n:p.detach().cpu().clone() for n,p in params.items()}
        updates = epoch(model, params, tok, config=config, output=output)
        changed = sum(not torch.equal(original[n], p.detach().cpu()) for n,p in params.items())
        assert changed > 0
        model.save_pretrained(output/'adapter', safe_serialization=True)
        tok.save_pretrained(output/'adapter')
        torch.save(probe(model, read(ROOT/'eval_encoded.json')[0]['variants'][0]), output/'reference_logits.pt')
        result = dict(status='completed', inputs_seen=189, responses_seen=197, updates=len(updates),
            changed_tensors=changed, environment=environment, manifest_sha256=sha(ROOT/'manifest.json'),
            adapter_files={p.name:sha(p) for p in (output/'adapter').iterdir() if p.is_file()},
            peak_allocated_bytes=torch.cuda.max_memory_allocated(), test_used=False)
        save(output/'result.json', result)
        save(output/'progress.json', dict(phase='completed', result=result))
    except BaseException as error:
        save(output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()

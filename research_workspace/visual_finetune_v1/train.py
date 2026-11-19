"""从基础权重独立开始；所有训练样本恰好一次，不复用smoke权重。"""
import time
import traceback
import torch
from vf_common import ROOT, runtime, config, rows, processor, encoded, read, save, sha, verify
from vf_update import update
from smoke import probe
from stability.sft_data import epoch_groups

CHECKPOINT_INTERVAL = 5


def checkpoint(model, output, *, step, optimizer, scaler):
    folder = output/f'checkpoint_{step:03d}'
    folder.mkdir(exist_ok=False)
    model.save_pretrained(folder/'adapter', safe_serialization=True)
    torch.save(dict(optimizer=optimizer.state_dict(), scaler=scaler.state_dict(),
        torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all(), step=step),
        folder/'training_state.pt')


def train_epoch(model, params, *, settings, output, proc, data):
    groups = epoch_groups(len(data), accumulation=settings['accumulation'], seed=settings['seed'])
    save(output/'epoch_order.json', groups)
    optimizer = torch.optim.AdamW(params.values(), lr=settings['learning_rate'])
    scaler = torch.amp.GradScaler('cuda', init_scale=settings['amp_init_scale'])
    started, updates = time.monotonic(), []
    for step, indices in enumerate(groups, 1):
        values = [encoded(data[i], proc) for i in indices]
        result = update(model, params, rows=values, optimizer=optimizer, scaler=scaler)
        result.update(step=step, indices=indices, elapsed_s=time.monotonic()-started,
            peak_allocated_bytes=torch.cuda.max_memory_allocated())
        save(output/'updates'/f'{step:03d}.json', result)
        updates.append(result)
        print(result, flush=True)
        if step % CHECKPOINT_INTERVAL == 0 or step == len(groups):
            checkpoint(model, output, step=step, optimizer=optimizer, scaler=scaler)
    assert sorted(i for row in updates for i in row['indices']) == list(range(len(data)))
    return updates


def main():
    settings = config()
    smoke = verify(ROOT/'smoke/passed.json')
    assert smoke['passed'] and smoke['manifest_sha256'] == sha(ROOT/'manifest.json')
    output = ROOT/'training'
    output.mkdir(exist_ok=False)
    try:
        model, params, _, environment = runtime.setup(settings)
        original = {n: p.detach().cpu().clone() for n, p in params.items()}
        data, proc = rows(settings), processor(settings)
        updates = train_epoch(model, params, settings=settings, output=output, proc=proc, data=data)
        changed = sum(not torch.equal(original[n], p.detach().cpu()) for n, p in params.items())
        assert changed > 0
        model.save_pretrained(output/'adapter', safe_serialization=True)
        proc.save_pretrained(output/'processor')
        torch.save(probe(model, encoded(data[0], proc)), output/'reference_logits.pt')
        config()
        files = [*list((output/'adapter').glob('*')), output/'reference_logits.pt', output/'epoch_order.json']
        save(output/'result.json', dict(status='completed', updates=len(updates), samples_seen=len(data),
            changed_tensors=changed, environment=environment, test_used=False,
            reference_input=data[0]['input_id'], manifest_sha256=sha(ROOT/'manifest.json'),
            identities={str(p): sha(p) for p in files if p.is_file()},
            limitation='Training completion is not physical performance improvement'))
    except BaseException as error:
        save(output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()

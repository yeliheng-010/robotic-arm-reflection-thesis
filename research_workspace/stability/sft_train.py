"""163条数据的独立初步QLoRA：完整epoch、独立验证、保存重载。"""
import json
import math
from pathlib import Path
import time
import traceback
import torch
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.sft_data import encode, epoch_groups, read_split
from stability.sft_evaluate import token_count, validation_loss, previews, save_reload
from stability.sft_freeze import code_hashes, file_hash
from stability.sft_model import device_setup, tokenizer, load_model, batch

CHECKPOINT_INTERVAL = 5


def load_data(config, tokenizer):
    directory = Path(config['dataset'])
    assert file_hash(directory/'manifest.json') == config['dataset_manifest_sha256']
    data = {}
    for split in ('train', 'validation'):
        rows = read_split(directory, split)
        data[split] = {'raw': rows, 'encoded': [encode(tokenizer, r['messages'],
                              max_length=config['max_length']) for r in rows]}
    assert not ({r['metadata']['prompt_sha256'] for r in data['train']['raw']} &
                {r['metadata']['prompt_sha256'] for r in data['validation']['raw']})
    return data


def optimizer_step(model, params, *, rows, optimizer, scaler):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    total = sum(token_count(r) for r in rows)
    measured = 0.
    for row in rows:
        with torch.autocast('cuda', dtype=torch.float16):
            loss = model(**batch(row)).loss
        value = loss.detach().float().item()
        assert math.isfinite(value), 'Nonfinite training loss'
        weight = token_count(row)/total
        measured += value*weight
        scaler.scale(loss*weight).backward()
    scaler.unscale_(optimizer)
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in params.values())
    norm = torch.nn.utils.clip_grad_norm_(list(params.values()), 1.).item()
    assert math.isfinite(norm) and norm > 0, 'Invalid gradient norm'
    old_scale = scaler.get_scale()
    scaler.step(optimizer)
    scaler.update()
    assert scaler.get_scale() >= old_scale, 'AMP skipped an optimizer update'
    torch.cuda.synchronize()
    optimizer.zero_grad(set_to_none=True)
    return {'loss': measured, 'gradient_norm': norm, 'samples': len(rows), 'supervised_tokens': total}


def checkpoint(context, output, *, step, order):
    directory = output/f'checkpoint_{step:05d}'
    context['model'].save_pretrained(directory, safe_serialization=True)
    context['tokenizer'].save_pretrained(directory)
    torch.save({'optimizer': context['optimizer'].state_dict(), 'scaler': context['scaler'].state_dict(),
        'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(),
        'step': step, 'epoch_groups': order}, directory/'training_state.pt')


def train_epoch(context, config, output):
    rows = context['data']['train']['encoded']
    order = epoch_groups(len(rows), accumulation=config['accumulation'], seed=config['seed'])
    atomic(output/'epoch_order.json', order)
    started, updates = time.monotonic(), []
    for step, indices in enumerate(order, 1):
        update = optimizer_step(context['model'], context['params'], rows=[rows[i] for i in indices],
                                optimizer=context['optimizer'], scaler=context['scaler'])
        update.update(step=step, total_steps=len(order), elapsed_s=time.monotonic()-started,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      peak_reserved_bytes=torch.cuda.max_memory_reserved())
        updates.append(update)
        with (output/'updates.jsonl').open('a') as stream:
            stream.write(json.dumps(update)+'\n')
        atomic(output/'progress.json', {'phase': 'training', 'last_update': update})
        print(json.dumps(update), flush=True)
        if step % CHECKPOINT_INTERVAL == 0 or step == len(order):
            checkpoint(context, output, step=step, order=order)
    assert sum(u['samples'] for u in updates) == len(rows)
    return updates


def run(config, output, result):
    result['environment'] = device_setup(config['seed'])
    tok = tokenizer(config['model'])
    data = load_data(config, tok)
    atomic(output/'progress.json', {'phase': 'loading_model'})
    model, params = load_model(config)
    result['trainable_parameters'] = sum(p.numel() for p in params.values())
    original = {n: p.detach().cpu().clone() for n, p in params.items()}
    atomic(output/'progress.json', {'phase': 'baseline_validation'})
    result['validation_before'] = validation_loss(model, data['validation']['encoded'])
    atomic(output/'metrics.json', result)
    result['previews_before'] = previews(model, tok, rows=data['validation']['raw'], output=output/'before.json')
    context = dict(model=model, params=params, tokenizer=tok, data=data,
        optimizer=torch.optim.AdamW(params.values(), lr=config['learning_rate']),
        scaler=torch.amp.GradScaler('cuda', init_scale=config['amp_init_scale']))
    torch.cuda.reset_peak_memory_stats()
    result['updates'] = train_epoch(context, config, output)
    result['changed_adapter_tensors'] = sum(not torch.equal(original[n], p.detach().cpu()) for n, p in params.items())
    assert result['changed_adapter_tensors'] > 0
    atomic(output/'progress.json', {'phase': 'final_validation'})
    result['validation_after'] = validation_loss(model, data['validation']['encoded'])
    result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
    atomic(output/'metrics.json', result)
    del context, params, original
    model, error = save_reload(model, tok, row=data['validation']['encoded'][0], output=output/'adapter')
    result['adapter_reload_max_logit_error'] = error
    result['previews_after'] = previews(model, tok, rows=data['validation']['raw'], output=output/'after.json')
    result['adapter_files'] = {p.name: file_hash(p) for p in (output/'adapter').iterdir() if p.is_file()}
    result.update(status='completed', test_used=False, physics_evaluated=False,
                  adapter=str(output/'adapter'), train_samples_seen=len(data['train']['raw']))


def main():
    output = OUT/'pilot_sft_v1'
    config = json.loads((output/'manifest.json').read_text())
    assert config['code'] == code_hashes(), 'Frozen training code changed'
    assert not (output/'result.json').exists() and not (output/'updates.jsonl').exists()
    result = {'status': 'running', 'started_at': time.time(), 'purpose': config['purpose']}
    try:
        run(config, output, result)
    except BaseException as error:
        result.update(status='failed', error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(output/'result.json', result)
        atomic(output/'progress.json', {'phase': result['status'], 'error': result.get('error')})
        print(json.dumps({k: result.get(k) for k in ('status', 'error', 'adapter')}), flush=True)


if __name__ == '__main__':
    main()

"""完整一轮扩大数据训练，支持独立进程从完整checkpoint恢复。"""
import argparse
import json
from pathlib import Path
import time
import traceback
import torch
from round2.checkpoint import save_bundle, restore_bundle
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.sft_data import epoch_groups
from stability.sft_evaluate import previews, save_reload, validation_loss
from stability.sft_freeze import code_hashes, file_hash
from stability.sft_model import device_setup, load_model, tokenizer
from stability.sft_train import load_data, optimizer_step

RUN = OUT/'round2_sft_v1'


def verify_config():
    config = json.loads((RUN/'manifest.json').read_text())
    assert config['code'] == code_hashes(), 'Frozen legacy code changed'
    assert config['epochs'] == 1
    for path, expected in config['source_identity'].items():
        assert file_hash(Path(path)) == expected, 'Round2 source changed: '+path
    for name, expected in config['model_files'].items():
        assert file_hash(Path(config['model'])/name) == expected, 'Base model changed'
    assert not (RUN/'result.json').exists(), 'Preserve finished result'
    return config


def setup(config):
    environment = device_setup(config['seed'])
    tok = tokenizer(config['model'])
    data = load_data(config, tok)
    model, params = load_model(config)
    original = {n: p.detach().cpu().clone() for n, p in params.items()}
    context = dict(model=model, params=params, tokenizer=tok, data=data,
        optimizer=torch.optim.AdamW(params.values(), lr=config['learning_rate']),
        scaler=torch.amp.GradScaler('cuda', init_scale=config['amp_init_scale']))
    return context, original, environment


def starting_state(context, config, resume):
    rows = context['data']['train']['encoded']
    order = epoch_groups(len(rows), accumulation=config['accumulation'], seed=config['seed'])
    if resume:
        meta = restore_bundle(context, Path(resume), file_hash(RUN/'manifest.json'))
        assert meta['order'] == order and meta['step'] == len(meta['updates'])
        result = meta['result']
        result.setdefault('resume_events', []).append(dict(checkpoint=resume,
            restored_step=meta['step'], at=time.time(), fresh_process=True))
        return order, meta['updates'], result
    assert not (RUN/'progress.json').exists(), 'Existing run requires explicit resume'
    atomic(RUN/'epoch_order.json', order)
    atomic(RUN/'progress.json', {'phase': 'baseline_validation'})
    result = dict(started_at=time.time(), purpose=config['purpose'], test_used=False,
        validation_before=validation_loss(context['model'], context['data']['validation']['encoded']))
    result['previews_before'] = previews(context['model'], context['tokenizer'],
        rows=context['data']['validation']['raw'], output=RUN/'before.json')
    atomic(RUN/'baseline.json', result)
    return order, [], result


def epoch(context, config, state):
    order, updates, result, stop_after = state
    start = len(updates)
    for step in range(start+1, len(order)+1):
        indices = order[step-1]
        update = optimizer_step(context['model'], context['params'],
            rows=[context['data']['train']['encoded'][i] for i in indices],
            optimizer=context['optimizer'], scaler=context['scaler'])
        update.update(step=step, total_steps=len(order), at=time.time(), indices=indices,
            peak_allocated_bytes=torch.cuda.max_memory_allocated())
        updates.append(update)
        atomic(RUN/'updates.json', updates)
        atomic(RUN/'progress.json', dict(phase='training', last_update=update))
        print(json.dumps(update), flush=True)
        if step % config['checkpoint_interval'] == 0 or step in (stop_after, len(order)):
            meta = dict(identity=file_hash(RUN/'manifest.json'), step=step,
                        order=order, updates=updates, result=result)
            save_bundle(context, RUN/f'checkpoint_{step:05d}', meta)
        if step == stop_after:
            atomic(RUN/'pause_result.json', dict(status='checkpointed', step=step,
                purpose='intentional_fresh_process_resume_verification'))
            return False
    assert sum(u['samples'] for u in updates) == len(context['data']['train']['raw'])
    assert sorted(i for u in updates for i in u['indices']) == list(range(1002))
    result['updates'] = updates
    return True


def finish(context, original, result):
    model, tok, data = context['model'], context['tokenizer'], context['data']
    result['changed_adapter_tensors'] = sum(not torch.equal(original[n], p.detach().cpu())
                                         for n, p in context['params'].items())
    assert result['changed_adapter_tensors'] > 0
    atomic(RUN/'progress.json', {'phase': 'final_validation'})
    result['validation_after'] = validation_loss(model, data['validation']['encoded'])
    result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
    atomic(RUN/'metrics.json', result)
    context.clear()
    model, error = save_reload(model, tok, row=data['validation']['encoded'][0], output=RUN/'adapter')
    result['adapter_reload_max_logit_error'] = error
    result['previews_after'] = previews(model, tok, rows=data['validation']['raw'], output=RUN/'after.json')
    result['adapter_files'] = {p.name: file_hash(p) for p in (RUN/'adapter').iterdir() if p.is_file()}
    result.update(status='completed', test_used=False, physics_evaluated=False,
        adapter=str(RUN/'adapter'), train_samples_seen=len(data['train']['raw']), ended_at=time.time())
    atomic(RUN/'result.json', result)
    atomic(RUN/'progress.json', {'phase': 'completed'})
    print(json.dumps({k: result[k] for k in ('status', 'train_samples_seen', 'validation_after')}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume')
    parser.add_argument('--stop-after', type=int, default=0)
    args = parser.parse_args()
    config = verify_config()
    context, original, environment = setup(config)
    order, updates, result = starting_state(context, config, args.resume)
    result['environment'] = environment
    result['trainable_parameters'] = sum(p.numel() for p in context['params'].values())
    try:
        if epoch(context, config, (order, updates, result, args.stop_after)):
            finish(context, original, result)
    except BaseException as error:
        atomic(RUN/f'failure_{int(time.time())}.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()

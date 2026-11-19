"""Single-GPU 7B QLoRA runtime check, not a held-out robotics evaluation."""
import argparse
import gc
import functools
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import random
import time
import traceback

from data import encode_example


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temporary.replace(path)


def run(args, result):
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    model_class = AutoModelForCausalLM
    template_kwargs = {}
    if args.architecture == 'qwen35':
        from transformers import AutoModelForImageTextToText
        model_class = AutoModelForImageTextToText
        template_kwargs = {'enable_thinking': False}
        if args.qwen35_fp32_delta:
            # The reference delta-rule explicitly casts to float32, but an outer
            # AMP context can downcast its matmuls again. Keep the recurrence and
            # triangular solves in float32 without changing the installed library.
            from transformers.models.qwen3_5 import modeling_qwen3_5 as implementation

            def keep_fp32(function):
                @functools.wraps(function)
                def forward(*values, **kwargs):
                    with torch.autocast('cuda', enabled=False):
                        return function(*values, **kwargs)
                return forward

            for name in ('torch_chunk_gated_delta_rule', 'torch_recurrent_gated_delta_rule'):
                setattr(implementation, name, keep_fp32(getattr(implementation, name)))
            result['qwen35_delta_precision'] = 'fp32_reference_without_autocast'

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('This smoke check requires exactly one scheduler-assigned CUDA device')
    torch.cuda.set_device(0)
    if 'sm_70' not in torch.cuda.get_arch_list():
        raise RuntimeError('Installed PyTorch wheel does not include V100 sm_70 kernels')
    torch.backends.cuda.enable_flash_sdp(False)
    device = torch.cuda.get_device_properties(0)
    result.update({
        'device': {'name': device.name, 'total_memory_bytes': device.total_memory,
                   'capability': list(torch.cuda.get_device_capability(0))},
        'versions': {name: importlib.metadata.version(name) for name in (
            'torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes', 'safetensors')},
        'pytorch_cuda': torch.version.cuda,
        'visible_devices': __import__('os').environ.get('CUDA_VISIBLE_DEVICES'),
        'slurm_job_id': __import__('os').environ.get('SLURM_JOB_ID'),
    })
    data_bytes = args.data.read_bytes()
    rows = [json.loads(line) for line in data_bytes.decode().splitlines() if line.strip()]
    if not rows:
        raise ValueError('Dataset is empty')
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, trust_remote_code=False)
    encoded = [encode_example(tokenizer, row['messages'], args.max_length, template_kwargs) for row in rows]
    result['data'] = {'samples': len(rows), 'sha256': hashlib.sha256(data_bytes).hexdigest(),
                      'token_lengths': [len(row['input_ids']) for row in encoded],
                      'supervised_tokens': [sum(t != -100 for t in row['labels']) for row in encoded],
                      'held_out_evaluation': False}
    progress_path = args.output / 'training_progress.json'
    write_json(progress_path, {'phase': 'loading_4bit_model', 'data': result['data']})
    quantization = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,
    )
    model = model_class.from_pretrained(
        args.model, local_files_only=True, trust_remote_code=False,
        quantization_config=quantization, torch_dtype=torch.float16,
        device_map={'': 0}, attn_implementation='eager' if args.architecture == 'qwen35' else 'sdpa',
    )
    if not getattr(model, 'is_loaded_in_4bit', False):
        raise RuntimeError('Model was not loaded in 4-bit mode')
    model.config.use_cache = False
    if hasattr(model.config, 'text_config'):
        model.config.text_config.use_cache = False
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={'use_reentrant': False},
    )
    model = get_peft_model(model, LoraConfig(
        task_type='CAUSAL_LM', r=args.rank, lora_alpha=args.rank * 2, lora_dropout=0.05,
        target_modules=(r'.*language_model\.layers\.\d+\.(?:self_attn|linear_attn|mlp)\.'
                        r'(?:q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj|'
                        r'in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)'
                        if args.architecture == 'qwen35' else
                        ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']),
        bias='none',
    ))
    trainable = {name: value for name, value in model.named_parameters() if value.requires_grad}
    if not trainable or any('lora_' not in name for name in trainable):
        raise RuntimeError('Expected only LoRA adapter parameters to be trainable')
    original = {name: value.detach().cpu().clone() for name, value in trainable.items()}
    result['trainable_parameters'] = sum(value.numel() for value in trainable.values())
    result['model_memory_footprint_bytes'] = model.get_memory_footprint()
    optimizer = torch.optim.AdamW(trainable.values(), lr=args.learning_rate)
    scaler = torch.amp.GradScaler('cuda', init_scale=args.amp_init_scale)

    def batch(index):
        return {key: torch.tensor([value], device='cuda') for key, value in encoded[index].items()}

    @torch.no_grad()
    def measured_loss():
        model.eval()
        with torch.autocast('cuda', dtype=torch.float16):
            loss = model(**batch(0)).loss.float().item()
        if not math.isfinite(loss):
            raise RuntimeError('Nonfinite measured loss')
        return loss

    result['before_training_loss_on_first_sample'] = measured_loss()
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    updates = []
    for step in range(args.steps):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        losses = []
        for microstep in range(args.gradient_accumulation):
            index = (step * args.gradient_accumulation + microstep) % len(encoded)
            with torch.autocast('cuda', dtype=torch.float16):
                loss = model(**batch(index)).loss
            raw_loss = loss.detach().float().item()
            if not math.isfinite(raw_loss):
                raise RuntimeError('Nonfinite training loss')
            losses.append(raw_loss)
            scaler.scale(loss / args.gradient_accumulation).backward()
        scaler.unscale_(optimizer)
        invalid = [name for name, value in trainable.items()
                   if value.grad is not None and not torch.isfinite(value.grad).all()]
        if invalid:
            result['invalid_gradient_parameters'] = invalid
            result['failed_step'] = step + 1
            result['amp_scale_at_failure'] = scaler.get_scale()
            raise RuntimeError(f'Nonfinite gradients in {len(invalid)} adapter tensors')
        norm = torch.nn.utils.clip_grad_norm_(list(trainable.values()), 1.0).item()
        if not math.isfinite(norm) or norm <= 0:
            raise RuntimeError('Nonfinite or zero gradient norm')
        old_scale = scaler.get_scale()
        scaler.step(optimizer)
        scaler.update()
        if scaler.get_scale() < old_scale:
            raise RuntimeError('AMP skipped an optimizer step')
        torch.cuda.synchronize()
        update = {'step': step + 1, 'loss': sum(losses) / len(losses),
                  'gradient_norm': norm, 'elapsed_s': time.monotonic() - started,
                  'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
                  'peak_reserved_bytes': torch.cuda.max_memory_reserved()}
        updates.append(update)
        write_json(progress_path, {'phase': 'training', 'last_update': update})
        print(json.dumps(update), flush=True)
    optimizer.zero_grad(set_to_none=True)
    result['updates'] = updates
    result['train_elapsed_s'] = time.monotonic() - started
    result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
    result['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
    result['after_training_loss_on_first_sample'] = measured_loss()
    changed = [name for name, value in trainable.items() if not torch.equal(original[name], value.detach().cpu())]
    if not changed:
        raise RuntimeError('No adapter tensor changed')
    result['changed_adapter_tensors'] = len(changed)
    adapter_dir = args.output / 'adapter'
    model.save_pretrained(adapter_dir, safe_serialization=True)
    tokenizer.save_pretrained(adapter_dir)
    write_json(progress_path, {'phase': 'checking_adapter_reload'})
    model.eval()
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.float16):
        reference = model(**batch(0)).logits[:, -1, :].detach().float().cpu()
    # Release adapter/optimizer references before checking saved weights against the same frozen base.
    del optimizer, trainable, original
    base_model = model.unload()
    del model
    gc.collect()
    torch.cuda.empty_cache()
    model = PeftModel.from_pretrained(base_model, adapter_dir, is_trainable=False, local_files_only=True)
    model.eval()
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.float16):
        restored = model(**batch(0)).logits[:, -1, :].detach().float().cpu()
    max_error = (reference - restored).abs().max().item()
    result['adapter_reload_max_logit_error'] = max_error
    if not torch.allclose(reference, restored, atol=0.02, rtol=0.002):
        raise RuntimeError('Reloaded adapter did not reproduce saved model logits')
    model.gradient_checkpointing_disable()
    prompt = tokenizer.apply_chat_template(rows[0]['messages'][:-1], tokenize=False,
                                           add_generation_prompt=True, **template_kwargs)
    inputs = tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.float16):
        generated = model.generate(**inputs, max_new_tokens=96, do_sample=False,
                                   use_cache=True, pad_token_id=tokenizer.eos_token_id)
    text = tokenizer.decode(generated[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    result['generation_on_training_prompt'] = text
    try:
        parsed = json.loads(text)
        result['generation_is_json'] = isinstance(parsed, dict)
    except ValueError:
        result['generation_is_json'] = False
    result['adapter_path'] = str(adapter_dir)
    result['adapter_files'] = {
        p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in adapter_dir.iterdir() if p.is_file()
    }
    result['status'] = 'passed'
    write_json(progress_path, {'phase': 'complete', 'successful_optimizer_steps': len(updates)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--architecture', choices=('causal', 'qwen35'), default='causal')
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=8)
    parser.add_argument('--max-length', type=int, default=512)
    parser.add_argument('--gradient-accumulation', type=int, default=2)
    parser.add_argument('--rank', type=int, default=8)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--amp-init-scale', type=float, default=256)
    parser.add_argument('--qwen35-fp32-delta', action='store_true')
    args = parser.parse_args()
    if min(args.steps, args.max_length, args.gradient_accumulation, args.rank) <= 0:
        parser.error('Training dimensions must be positive')
    if not math.isfinite(args.amp_init_scale) or args.amp_init_scale <= 0:
        parser.error('--amp-init-scale must be finite and positive')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output must be a new empty directory')
    args.output.mkdir(parents=True, exist_ok=True)
    result = {'status': 'running', 'purpose': 'runtime_smoke_only',
              'limitations': 'No held-out test; training loss and generation do not measure robotics success.',
              'arguments': {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
              'started_at': time.time()}
    try:
        run(args, result)
    except BaseException as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        try:
            import torch
            if torch.cuda.is_initialized():
                result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
                result['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        except Exception:
            pass
        result['finished_at'] = time.time()
        write_json(args.output / 'smoke_result.json', result)
        print(json.dumps({k: result.get(k) for k in ('status', 'error', 'peak_allocated_bytes', 'peak_reserved_bytes', 'adapter_path')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

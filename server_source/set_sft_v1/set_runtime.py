"""复用稳定4B加载，新增按输入等权的流式反传和集合评价。"""
import json
import math
from contextlib import nullcontext
import torch
from runtime import setup
from loss import suffix_loss, supervised_start
from objective import weighted_variants, score_text


def optimizer_step(model, params, *, groups, optimizer, scaler):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    measured, tokens, responses = 0., 0, 0
    for row, weight in weighted_variants(groups):
        with torch.autocast('cuda', dtype=torch.float16):
            loss = suffix_loss(model, row)
        value = float(loss.detach())
        assert math.isfinite(value), 'Nonfinite loss'
        measured += value*weight
        scaler.scale(loss*weight).backward()
        tokens += len(row['labels'])-supervised_start(row)
        responses += 1
    scaler.unscale_(optimizer)
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in params.values())
    norm = float(torch.nn.utils.clip_grad_norm_(list(params.values()), 1.0))
    assert math.isfinite(norm) and norm > 0
    previous = scaler.get_scale()
    scaler.step(optimizer)
    scaler.update()
    assert scaler.get_scale() >= previous, 'AMP skipped optimizer update'
    torch.cuda.synchronize()
    optimizer.zero_grad(set_to_none=True)
    return dict(loss=measured, gradient_norm=norm, inputs=len(groups), responses=responses,
                supervised_tokens=tokens, weighting='mean_inputs_mean_successes_mean_tokens')


def predict(model, tok, encoded, *, raw, baseline=False):
    model.eval()
    first = encoded['variants'][0]
    start = supervised_start(first)
    ids = torch.tensor([first['input_ids'][:start]], device='cuda')
    context = model.disable_adapter() if baseline else nullcontext()
    with context, torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
        losses = [float(suffix_loss(model, r)) for r in encoded['variants']]
        output = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
            max_new_tokens=128, do_sample=False, use_cache=True, logits_to_keep=1,
            pad_token_id=tok.pad_token_id)
    assert all(math.isfinite(value) for value in losses)
    generated = output[0, start:]
    text = tok.decode(generated, skip_special_tokens=True)
    eos = model.generation_config.eos_token_id
    eos = [eos] if isinstance(eos, int) else eos
    finished = bool(len(generated) and int(generated[-1]) in eos)
    candidates = [r['id'] for r in json.loads(raw['messages'][1]['content'])['candidates']]
    score = score_text(text, candidates=candidates, accepted=raw['accepted_action_ids'])
    score['candidate_valid'] = score['candidate_valid'] and finished
    score['set_match'] = score['set_match'] and finished
    return dict(text=text, loss=sum(losses)/len(losses), per_target_losses=losses,
        output_tokens=len(generated), generated_ids=generated.tolist(), eos_ids=eos, finished=finished,
        diagnostic_match=bool(score['candidate_valid'] and raw.get('diagnostic_target') == score['action_id']), **score)

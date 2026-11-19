"""独立validation损失和冻结开发例输出，不接触test。"""
import gc
import json
import math
import torch
from peft import PeftModel
from stability.collection_status import atomic
from stability.sft_model import batch


def token_count(row):
    return sum(t != -100 for t in row['labels'][1:])


@torch.no_grad()
def validation_loss(model, rows):
    model.eval()
    total, tokens = 0., 0
    for row in rows:
        with torch.autocast('cuda', dtype=torch.float16):
            loss = model(**batch(row)).loss.float().item()
        assert math.isfinite(loss)
        count = token_count(row)
        total += loss*count
        tokens += count
    return {'loss': total/tokens, 'supervised_tokens': tokens, 'samples': len(rows)}


def preview_indices(rows):
    indices, faults = [], set()
    for index, row in enumerate(rows):
        fault = row['metadata']['fault']
        if fault not in faults:
            indices.append(index)
            faults.add(fault)
    return indices


@torch.no_grad()
def previews(model, tokenizer, *, rows, output):
    model.eval()
    results = []
    for index in preview_indices(rows):
        row = rows[index]
        prompt = tokenizer.apply_chat_template(row['messages'][:-1], tokenize=False,
                                               add_generation_prompt=True, enable_thinking=False)
        inputs = tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
        with torch.autocast('cuda', dtype=torch.float16):
            tokens = model.generate(**inputs, max_new_tokens=256, do_sample=False,
                use_cache=True, pad_token_id=tokenizer.eos_token_id)
        raw = tokenizer.decode(tokens[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        expected = json.loads(row['messages'][-1]['content'])
        try:
            answer = json.loads(raw)
            valid = isinstance(answer, dict) and isinstance(answer.get('changes'), dict)
            exact = valid and answer['changes'] == expected['changes']
        except ValueError:
            valid, exact = False, False
        results.append({'validation_index': index, 'task_id': row['metadata']['task_id'],
            'fault': row['metadata']['fault'], 'raw_output': raw, 'expected': expected,
            'json_with_changes': valid, 'changes_exact_match': exact})
        atomic(output, {'purpose': 'three_development_previews_not_physical_evaluation', 'results': results})
    return results


@torch.no_grad()
def save_reload(model, tokenizer, *, row, output):
    model.eval()
    model.save_pretrained(output, safe_serialization=True)
    tokenizer.save_pretrained(output)
    with torch.autocast('cuda', dtype=torch.float16):
        expected = model(**batch(row)).logits[:, -1, :].float().cpu()
    base = model.unload()
    gc.collect()
    torch.cuda.empty_cache()
    restored = PeftModel.from_pretrained(base, output, is_trainable=False, local_files_only=True)
    restored.eval()
    with torch.autocast('cuda', dtype=torch.float16):
        actual = restored(**batch(row)).logits[:, -1, :].float().cpu()
    assert torch.allclose(expected, actual, atol=.02, rtol=.002)
    return restored, (expected-actual).abs().max().item()

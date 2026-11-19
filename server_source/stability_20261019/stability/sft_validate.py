"""保存后独立加载adapter，在全部validation上自由生成；不读test。"""
import json
import time
import torch
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.sft_data import encode, read_split
from stability.sft_freeze import file_hash
from stability.sft_model import batch, device_setup, load_model, tokenizer


@torch.no_grad()
def manual_loss(model, row):
    tensors = batch(row)
    with torch.autocast('cuda', dtype=torch.float16):
        output = model(**tensors)
    logits = output.logits[:, :-1].float().contiguous()
    targets = tensors['labels'][:, 1:].contiguous()
    independent = torch.nn.functional.cross_entropy(
        logits.reshape(-1, logits.shape[-1]), targets.reshape(-1), ignore_index=-100)
    difference = abs(independent.item()-output.loss.item())
    assert difference < 1e-6, 'Shifted CE differs from library loss'
    return dict(manual_shifted_ce=independent.item(), library_loss=output.loss.item(), difference=difference)


@torch.no_grad()
def generate(model, tok, row):
    prompt = tok.apply_chat_template(row['messages'][:-1], tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    inputs = tok(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
    with torch.autocast('cuda', dtype=torch.float16):
        output = model.generate(**inputs, do_sample=False, max_new_tokens=256,
            use_cache=True, pad_token_id=tok.eos_token_id)
    raw = tok.decode(output[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    expected = json.loads(row['messages'][-1]['content'])
    try:
        answer = json.loads(raw)
        valid = isinstance(answer, dict) and isinstance(answer.get('changes'), dict)
        exact = valid and answer['changes'] == expected['changes']
    except ValueError:
        valid, exact = False, False
    return dict(task_id=row['metadata']['task_id'], fault=row['metadata']['fault'],
        raw_output=raw, expected=expected, json_with_changes=valid, changes_exact_match=exact)


def main():
    output = OUT/'pilot_sft_v1'
    config = json.loads((output/'manifest.json').read_text())
    trained = json.loads((output/'result.json').read_text())
    assert trained['status'] == 'completed'
    assert file_hash(output/'adapter/adapter_model.safetensors') == trained['adapter_files']['adapter_model.safetensors']
    target = output/'validation_generation.json'
    assert not target.exists(), 'Preserve previous validation'
    environment = device_setup(config['seed'])
    tok, (model, _) = tokenizer(config['model']), load_model(config)
    model.load_adapter(output/'adapter', adapter_name='pilot', is_trainable=False)
    model.set_adapter('pilot')
    model.eval()
    rows = read_split(OUT/'pilot_sft_data_v1', 'validation')
    result = dict(status='running', environment=environment, test_used=False,
        physics_evaluated=False, purpose='validation_only_not_independent_test',
        script_sha256=file_hash(OUT/'stability/sft_validate.py'), results=[], started_at=time.time())
    result['manual_loss_check'] = manual_loss(model, encode(tok, rows[0]['messages'], max_length=4096))
    for row in rows:
        result['results'].append(generate(model, tok, row))
        atomic(target, result)
        print(json.dumps({'completed': len(result['results']), 'total': len(rows)}), flush=True)
    result.update(status='completed', ended_at=time.time(), samples=len(rows),
        json_with_changes=sum(r['json_with_changes'] for r in result['results']),
        changes_exact_match=sum(r['changes_exact_match'] for r in result['results']))
    atomic(target, result)


if __name__ == '__main__':
    main()

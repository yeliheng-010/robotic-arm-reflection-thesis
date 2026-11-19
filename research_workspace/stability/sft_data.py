"""独立小规模试训的数据和确定性epoch计划。"""
import hashlib
import json
import random


def encode(tokenizer, messages, *, max_length):
    options = dict(tokenize=False, enable_thinking=False)
    prompt = tokenizer.apply_chat_template(messages[:-1], add_generation_prompt=True, **options)
    full = tokenizer.apply_chat_template(messages, add_generation_prompt=False, **options)
    prefix = tokenizer(prompt, add_special_tokens=False)['input_ids']
    tokens = tokenizer(full, add_special_tokens=False)['input_ids']
    if tokens[:len(prefix)] != prefix or len(tokens) <= len(prefix):
        raise ValueError('Template prefix mismatch or no supervised answer')
    if len(tokens) > max_length:
        raise ValueError(f'Length {len(tokens)} exceeds {max_length}; no truncation permitted')
    return dict(input_ids=tokens, attention_mask=[1]*len(tokens),
                labels=[-100]*len(prefix)+tokens[len(prefix):])


def epoch_groups(size, *, accumulation, seed):
    if size <= 0 or accumulation <= 0:
        raise ValueError('Positive dimensions required')
    order = list(range(size))
    random.Random(seed).shuffle(order)
    return [order[i:i+accumulation] for i in range(0, size, accumulation)]


def validate_rows(rows, split):
    if split not in ('train', 'validation') or not rows:
        raise ValueError('Only nonempty train/validation can be read by the trainer')
    seen = set()
    for row in rows:
        meta = row['metadata']
        if meta['teacher_source'] != 'rule_expert' or meta['model'] is not None or meta['split'] != split:
            raise ValueError('Dataset source or split mismatch')
        if meta['prompt_sha256'] in seen:
            raise ValueError('Duplicate input')
        if [m['role'] for m in row['messages']] != ['system', 'user', 'assistant']:
            raise ValueError('Unexpected conversation roles')
        seen.add(meta['prompt_sha256'])


def read_split(directory, split):
    manifest = json.loads((directory/'manifest.json').read_text())
    if split not in ('train', 'validation'):
        raise ValueError('Test set is sealed during pilot training')
    data = (directory/f'{split}.jsonl').read_bytes()
    assert hashlib.sha256(data).hexdigest() == manifest['files'][split]['sha256']
    rows = [json.loads(line) for line in data.decode().splitlines() if line.strip()]
    validate_rows(rows, split)
    return rows

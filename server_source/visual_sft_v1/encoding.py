"""保留两幅实际 RGB；标签只覆盖真实 assistant 回答后缀。"""
from copy import deepcopy
import torch

MAX_INPUT_TOKENS = 16384


def suffix_labels(prompt_ids, full_ids):
    prompt, full = list(prompt_ids), list(full_ids)
    assert prompt and len(full)>len(prompt)
    assert full[:len(prompt)] == prompt, 'Chat template prefix changed'
    return [-100]*len(prompt)+full[len(prompt):]


def encode(processor, messages):
    assert [m['role'] for m in messages] == ['system','user','assistant']
    assert isinstance(messages[1]['content'],list)
    assert sum(c['type']=='image' for c in messages[1]['content']) == 2
    options = dict(tokenize=True, return_dict=True, return_tensors='pt', enable_thinking=False)
    prompt = processor.apply_chat_template(deepcopy(messages[:-1]), add_generation_prompt=True, **options)
    full = processor.apply_chat_template(deepcopy(messages), add_generation_prompt=False, **options)
    start = prompt['input_ids'].shape[1]
    assert start <= MAX_INPUT_TOKENS and full['input_ids'].shape[1] <= MAX_INPUT_TOKENS+256
    for key in ('pixel_values','image_grid_thw'):
        assert key in prompt and key in full and torch.equal(prompt[key],full[key])
    assert len(full['image_grid_thw']) == 2
    labels = suffix_labels(prompt['input_ids'][0].tolist(), full['input_ids'][0].tolist())
    full['labels'] = torch.tensor([labels],dtype=torch.long)
    return full, dict(prompt_tokens=start, answer_tokens=len(labels)-start,
        pixel_values_shape=list(full['pixel_values'].shape), image_grid_thw=full['image_grid_thw'].tolist(),
        assistant_only_mask=True, input_truncated=False)

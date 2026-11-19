"""两图完整上下文、仅答案后缀的因果损失。"""
import torch

IMAGE_FIELDS = ('pixel_values', 'image_grid_thw')


def boundary(values):
    ids, labels = values['input_ids'], values['labels']
    assert ids.ndim == 2 and ids.shape[0] == 1 and ids.shape == labels.shape
    positions = torch.nonzero(labels[0] != -100).flatten()
    assert positions.numel() and int(positions[0]) > 0
    start = int(positions[0])
    assert torch.equal(positions, torch.arange(start, ids.shape[1], device=positions.device))
    assert torch.equal(labels[:, start:], ids[:, start:])
    assert torch.equal(values['attention_mask'], torch.ones_like(ids))
    assert all(k in values for k in IMAGE_FIELDS)
    assert values['image_grid_thw'].shape == (2, 3)
    assert values['pixel_values'].numel() > 0
    return start


def suffix_logits(model, values):
    start = boundary(values)
    inputs = {k: v for k, v in values.items() if k != 'labels'}
    answer_size = values['input_ids'].shape[1] - start
    output = model(**inputs, logits_to_keep=answer_size + 1, use_cache=False)
    logits = output.logits[:, :-1, :]
    assert logits.shape[:2] == (1, answer_size)
    return logits, values['labels'][:, start:]


def objective(model, values):
    logits, targets = suffix_logits(model, values)
    return torch.nn.functional.cross_entropy(
        logits.float().reshape(-1, logits.shape[-1]), targets.reshape(-1))


def move(values, *, device='cuda'):
    return {k: v.to(device) for k, v in values.items()}

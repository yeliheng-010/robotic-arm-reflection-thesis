"""纯检查逻辑；不改变既定训练或推理行为。"""
import math
import torch

MAX_LOGIT_ERROR = 1e-4


def validate_update(row, *, step, size):
    assert row['step'] == step
    assert row['samples'] == len(row['indices']) == size
    assert math.isfinite(row['loss']) and row['loss'] >= 0
    assert math.isfinite(row['gradient_norm']) and row['gradient_norm'] > 0
    assert row['supervised_tokens'] > 0


def validate_training(result, updates, *, settings, manifest_sha256):
    assert result['status'] == 'completed' and result['test_used'] is False
    assert result['manifest_sha256'] == manifest_sha256
    assert result['changed_tensors'] > 0
    count, accumulation = settings['train_samples'], settings['accumulation']
    assert result['samples_seen'] == count and count > 0 and accumulation > 0
    assert result['updates'] == len(updates) == math.ceil(count / accumulation)
    seen = []
    for step, row in enumerate(updates, 1):
        validate_update(row, step=step, size=min(accumulation, count - len(seen)))
        seen.extend(row['indices'])
    assert sorted(seen) == list(range(count))


def compare_logits(expected, actual):
    assert expected.ndim == actual.ndim == 1
    assert expected.shape == actual.shape and expected.numel() > 0
    assert torch.isfinite(expected).all() and torch.isfinite(actual).all()
    error = float((expected.float() - actual.float()).abs().max())
    assert error <= MAX_LOGIT_ERROR, f'Final adapter reload logits mismatch: {error}'
    return error

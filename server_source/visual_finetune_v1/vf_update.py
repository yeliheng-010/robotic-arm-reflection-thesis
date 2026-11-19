"""完整图文前向，跨样本按答案token数量归一化梯度。"""
import math
import torch
from vt_objective import boundary, objective, move

MAX_GRAD_NORM = 1.0


def update(model, params, *, rows, optimizer, scaler, device='cuda'):
    assert rows
    model.train()
    optimizer.zero_grad(set_to_none=True)
    sizes = [row['labels'].shape[1] - boundary(row) for row in rows]
    total, measured = sum(sizes), 0.
    for row, size in zip(rows, sizes):
        with torch.autocast(device, dtype=torch.float16, enabled=device == 'cuda'):
            loss = objective(model, move(row, device=device))
        value = float(loss.detach())
        assert math.isfinite(value), 'Nonfinite loss'
        measured += value * size / total
        scaler.scale(loss * size / total).backward()
    scaler.unscale_(optimizer)
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in params.values())
    norm = float(torch.nn.utils.clip_grad_norm_(list(params.values()), MAX_GRAD_NORM))
    assert math.isfinite(norm) and norm > 0
    previous = scaler.get_scale()
    scaler.step(optimizer)
    scaler.update()
    assert scaler.get_scale() >= previous, 'AMP skipped update'
    if device == 'cuda':
        torch.cuda.synchronize()
    optimizer.zero_grad(set_to_none=True)
    return dict(loss=measured, gradient_norm=norm, samples=len(rows), supervised_tokens=total)

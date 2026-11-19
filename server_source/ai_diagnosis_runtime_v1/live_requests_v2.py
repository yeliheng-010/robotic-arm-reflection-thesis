"""仅适配执行器内存tuple；保持冻结v1白名单和公开JSON契约。"""
from copy import deepcopy
from live_requests import build as original_build


def build(ledger, record, *, sampler, telemetry, bridge):
    normalized = deepcopy(record)
    for name in ('grasp_offset', 'place_offset'):
        value = normalized['parameters'][name]
        if isinstance(value, tuple):
            normalized['parameters'][name] = list(value)
    return original_build(ledger, normalized, sampler=sampler, telemetry=telemetry, bridge=bridge)

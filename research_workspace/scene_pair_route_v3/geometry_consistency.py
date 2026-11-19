"""仅核对离线重建一致性，不改变规划和执行的物理门槛。"""
from math import isfinite

REBUILD_ATOL_M = 1e-6
SIZES = dict(source_center=3, source_half=3, bin_center=3,
             interior_half=2, usable_half=2, wall_top=1)
DYNAMIC = frozenset(('source_center', 'source_half', 'usable_half'))


def values(value, key):
    row = [value] if key == 'wall_top' else value
    assert isinstance(row, list) and len(row) == SIZES[key], key
    assert all(isinstance(v, (float, int)) and isfinite(v) for v in row), key
    return row


def compare(recorded, reconstructed):
    assert set(recorded) == set(reconstructed) == set(SIZES)
    differences = {}
    for key in SIZES:
        before, after = values(recorded[key], key), values(reconstructed[key], key)
        delta = max(abs(a-b) for a, b in zip(before, after))
        limit = REBUILD_ATOL_M if key in DYNAMIC else 0.
        assert delta <= limit, (key, delta, limit)
        differences[key] = delta
    return dict(max_abs_m=max(differences.values()), fields_max_abs_m=differences,
                reconstruction_atol_m=REBUILD_ATOL_M, static_fields_exact=True)

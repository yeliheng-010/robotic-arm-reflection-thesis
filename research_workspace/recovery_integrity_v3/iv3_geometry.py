"""识别动态重建超限用于拒绝监督；绝不将其变成通过。"""
from geometry_consistency import compare, values, SIZES, DYNAMIC, REBUILD_ATOL_M


class ReconstructionMismatch(Exception):
    def __init__(self, evidence):
        super().__init__('dynamic_geometry_reconstruction_exceeds_original_tolerance')
        self.evidence = evidence


def strict_compare(recorded, current):
    assert set(recorded) == set(current) == set(SIZES)
    differences = {}
    for key in SIZES:
        before, after = values(recorded[key], key), values(current[key], key)
        differences[key] = max(abs(a-b) for a, b in zip(before, after))
    assert all(differences[k] == 0. for k in SIZES if k not in DYNAMIC)
    exceeded = {k: v for k, v in differences.items() if k in DYNAMIC and v > REBUILD_ATOL_M}
    if exceeded:
        raise ReconstructionMismatch(dict(recorded=recorded, reconstructed=current,
            fields_max_abs_m=differences, exceeded=exceeded, original_atol_m=REBUILD_ATOL_M))
    return compare(recorded, current)

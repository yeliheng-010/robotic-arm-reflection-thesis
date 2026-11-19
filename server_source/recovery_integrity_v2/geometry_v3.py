"""组合量使用其输入误差传播，保留原单字段和物理检查。"""
from unittest.mock import patch
import numpy as np
from geometry_consistency import compare, REBUILD_ATOL_M
from goal_policy import EDGE_MARGIN_M

ROUNDING_ATOL_M = 1e-12


def placement(row, dimensions):
    center = np.array(row['target']) + np.array(dimensions['source_center']) - np.array(row['pose'])[:3, 3]
    footprint = np.abs(center[:2] - np.array(dimensions['bin_center'])[:2])
    footprint += np.array(dimensions['source_half'])[:2]
    margin = np.array(dimensions['interior_half']) - footprint
    gap = float(center[2] - dimensions['source_half'][2] - dimensions['wall_top'])
    return margin, gap


def reconstructed_placement(row, recorded, *, current):
    compare(recorded, current)
    _, cached_gap = placement(row, recorded)
    margin, gap = placement(row, current)
    assert abs(cached_gap - row['goal']['bottom_gap']) <= ROUNDING_ATOL_M
    propagated = (current['source_center'][2] - recorded['source_center'][2])
    propagated -= current['source_half'][2] - recorded['source_half'][2]
    assert abs((gap-cached_gap) - propagated) <= ROUNDING_ATOL_M
    assert abs(gap-cached_gap) <= 2 * REBUILD_ATOL_M + ROUNDING_ATOL_M
    assert np.all(margin > 0.) and np.all(margin >= EDGE_MARGIN_M - REBUILD_ATOL_M)
    assert gap > 0., 'Release bottom below wall top'
    return dict(edge_margin_m=margin.tolist(), bottom_gap_m=gap, strictly_inside_bin=True,
        gap_reconstruction_delta_m=gap-cached_gap, propagated_delta_m=propagated,
        per_field_atol_m=REBUILD_ATOL_M)


def audit(case, trace):
    import goal_audit_geometry as original
    evidence = {}
    original_ledger = original.endpoint_ledger

    def ledger(flow, current_trace):
        current = original.geometry(flow, current_trace['item'])
        recorded = current_trace['endpoints']['geometry']
        evidence.update(compare(recorded, current))
        endpoints = dict(current_trace['endpoints'], geometry=current)
        original_ledger(flow, dict(current_trace, endpoints=endpoints))
        if current_trace['selected'] is not None:
            evidence['placement'] = reconstructed_placement(current_trace['selected'], recorded, current=current)

    with patch.object(original, 'endpoint_ledger', ledger):
        result = original.audit(case, trace)
    return dict(result, reconstruction=evidence)

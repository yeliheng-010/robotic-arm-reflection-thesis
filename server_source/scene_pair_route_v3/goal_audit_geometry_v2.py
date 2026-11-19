"""保留原审计全部检查，仅区分缓存几何与qpos重建的数值一致性。"""
from unittest.mock import patch
import numpy as np
import goal_audit_geometry as original
from geometry_consistency import compare, REBUILD_ATOL_M
from goal_policy import EDGE_MARGIN_M


def reconstructed_placement(row, current):
    """以重建物体几何再次检查实际选中TCP所预测的箱内占用。"""
    grasp_center = np.array(row['pose'])[:3, 3]
    center = np.array(row['target']) + np.array(current['source_center']) - grasp_center
    footprint = np.abs(center[:2] - current['bin_center'][:2])
    footprint += np.array(current['source_half'])[:2]
    margin = np.array(current['interior_half']) - footprint
    gap = center[2] - current['source_half'][2] - current['wall_top']
    assert np.all(margin > 0.), 'Object footprint outside the bin'
    assert np.all(margin >= EDGE_MARGIN_M - REBUILD_ATOL_M)
    assert abs(gap - row['goal']['bottom_gap']) <= REBUILD_ATOL_M
    assert gap > 0., 'Release bottom below wall top'
    return dict(edge_margin_m=margin.tolist(), bottom_gap_m=float(gap),
                strictly_inside_bin=True)


def audit(case, trace):
    evidence = {}
    original_ledger = original.endpoint_ledger

    def ledger(flow, current_trace):
        current = original.geometry(flow, current_trace['item'])
        evidence.update(compare(current_trace['endpoints']['geometry'], current))
        # 只给原账本校验传递副本；目标复算仍使用原始记录，记录本身不变。
        endpoints = dict(current_trace['endpoints'], geometry=current)
        original_ledger(flow, dict(current_trace, endpoints=endpoints))
        if current_trace['selected'] is not None:
            evidence['placement'] = reconstructed_placement(current_trace['selected'], current)

    with patch.object(original, 'endpoint_ledger', ledger):
        result = original.audit(case, trace)
    return dict(result, reconstruction=evidence)

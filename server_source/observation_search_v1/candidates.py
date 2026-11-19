"""固定四轮反馈搜索；只使用观测资格与包围盒，不读位姿真值。"""
import numpy as np
from camera_joint_v1.policy import score
from coverage_repair_v1.proposals import changed, camera_key
from observation_search_v1.framing import recenter
from observation_search_v1.common import ROUND_BUDGET

ANCHORS = 4
DIVERSITY_SCALE = np.array([15., 8., .1, .04, .04])
ROUND_SCALES = (1., .5, .25, .125)


def vector(camera):
    return np.array([camera['azimuth_offset_deg'], camera['elevation_deg'],
                     camera['distance_m'], *camera['target'][:2]]) / DIVERSITY_SCALE


def anchors(rows):
    ranked = sorted([r for r in rows if 'gate' in r], key=score)
    selected = []
    for row in ranked:
        if all(np.linalg.norm(vector(row['camera'])-vector(s['camera'])) >= 1 for s in selected):
            selected.append(row)
        if len(selected) == ANCHORS:
            return selected
    selected.extend(r for r in ranked if r['index'] not in {s['index'] for s in selected})
    return selected[:ANCHORS]


def deltas(row, round_index):
    reasons = {reason for obj in row['gate']['objects'].values() for reason in obj.get('reasons', [])}
    scale = ROUND_SCALES[round_index]
    angular = [(20, 0, 0), (-20, 0, 0), (0, 8, 0), (0, -8, 0),
               (10, 8, 0), (-10, 8, 0), (20, -8, 0), (-20, -8, 0)]
    zoom = [(0, 0, -.08), (0, 0, -.16), (0, 5, -.08), (0, -5, -.08)]
    order = zoom+angular if reasons and reasons <= {'pixels', 'short_side', 'long_side'} else angular+zoom
    return [np.zeros(6)] + [np.array([a, e, d, 0, 0, 0])*scale for a, e, d in order]


def batch(rows, boxes, round_index):
    bounds = np.asarray(list(boxes.values()))
    center = (bounds[:, 0].min(axis=0) + bounds[:, 1].max(axis=0)) / 2
    selected = anchors(rows)
    seen = {camera_key(r['camera']) for r in rows if r.get('camera') is not None}
    proposals = []
    for offset_index in range(13):
        for anchor in selected:
            delta = deltas(anchor, round_index)[offset_index]
            camera = changed(anchor['camera'], delta, center)
            camera = recenter(camera, boxes, center) if camera is not None else None
            if camera is None or camera_key(camera) in seen:
                continue
            seen.add(camera_key(camera))
            proposals.append(dict(camera=camera, anchor_index=anchor['index'],
                offset_index=offset_index, delta=delta.tolist(), round=round_index))
            if len(proposals) == ROUND_BUDGET:
                return proposals
    return proposals

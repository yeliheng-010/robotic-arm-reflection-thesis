"""模型像素提示SAM，预测完全不读取仿真掩码。"""
import cv2
import numpy as np
from qualified_model_v1.policy import pixel

MIN_POINTS = 64
DEPTH_RANGE_M = (.05, 2.)


def select(results, *, shape, point):
    if not results or results[0].masks is None:
        return None, dict(accepted=False, reason='sam_no_masks')
    result, choices = results[0], []
    scores = result.boxes.conf.detach().cpu().numpy() if result.boxes is not None else None
    for index, tensor in enumerate(result.masks.data):
        mask = tensor.detach().cpu().numpy() >= .5
        if mask.shape != shape:
            mask = cv2.resize(mask.astype(np.uint8), shape[::-1], interpolation=cv2.INTER_NEAREST).astype(bool)
        if mask[point[1], point[0]]:
            confidence = float(scores[index]) if scores is not None else 0.
            choices.append((confidence, -int(mask.sum()), index, mask))
    if not choices:
        return None, dict(accepted=False, reason='sam_no_mask_contains_model_point')
    confidence, negative_area, index, mask = max(choices, key=lambda x: x[:3])
    return mask, dict(accepted=True, selected_index=index, confidence=confidence,
                      pixels=-negative_area, available_masks=len(result.masks.data))


def world_points(depth, mask, *, calibration):
    valid = mask & np.isfinite(depth) & (depth > DEPTH_RANGE_M[0]) & (depth < DEPTH_RANGE_M[1])
    v, u = np.where(valid)
    z = depth[v, u]
    fx, fy, cx, cy = calibration['intrinsics']
    camera = np.column_stack(((u-cx)*z/fx, (v-cy)*z/fy, z))
    transform = np.asarray(calibration['transform'])
    return camera@transform[:3, :3].T + transform[:3, 3]

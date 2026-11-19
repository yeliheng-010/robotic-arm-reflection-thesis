"""按原采样规则计算包围盒误差，保留每个像素。"""
import cv2
import numpy as np


def samples(depth, mask, *, transform, intrinsics, box, kernel):
    interior = cv2.erode(mask.astype(np.uint8), np.ones((kernel, kernel), np.uint8))
    pixels = np.argwhere(interior)
    pixels = pixels[::max(1, len(pixels) // 64)]
    if not len(pixels):
        return []
    v, u = pixels.T
    fx, fy, cx, cy = intrinsics
    z = depth[v, u]
    camera = np.column_stack(((u-cx)*z/fx, (v-cy)*z/fy, z))
    world = camera @ transform[:3, :3].T + transform[:3, 3]
    box = np.asarray(box)
    errors = np.max(np.maximum(box[0]-world, world-box[1]), axis=1)
    return [dict(v=int(y), u=int(x), depth_m=float(d), world=p.tolist(), outside_m=float(e))
            for y, x, d, p, e in zip(v, u, z, world, errors)]


def summary(rows):
    maximum = max([0.] + [r['outside_m'] for r in rows])
    return dict(passed=bool(rows) and maximum <= .006, samples=len(rows),
                max_outside_bounds_m=maximum, edge_kernel_pixels=3)

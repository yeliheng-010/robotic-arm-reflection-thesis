"""编译后的碰撞体与真实 mesh 顶点边界，包含子 body。"""
import numpy as np
from cl_geometry import geom_bounds
from sd_scene import compiled
from sd_config import MOVING


def root_boxes(model, data):
    grouped = {}
    for gid in range(model.ngeom):
        if not (model.geom_contype[gid] or model.geom_conaffinity[gid]):
            continue
        bid = int(model.body_rootid[model.geom_bodyid[gid]])
        if bid == 0:
            continue
        name = model.body(bid).name
        grouped.setdefault(name, []).append(geom_bounds(model, data, gid))
    return {name: [np.min(np.array(boxes)[:, 0], axis=0).tolist(),
                   np.max(np.array(boxes)[:, 1], axis=0).tolist()]
            for name, boxes in grouped.items()}


def inventory():
    model, data = compiled()
    boxes = root_boxes(model, data)
    return dict(boxes=boxes, table=boxes['simple_table'],
                positions={name: data.body(name).xpos.tolist() for name in MOVING},
                camera_position=data.cam_xpos[model.camera('cam').id].tolist(),
                camera_fovy=float(model.cam_fovy[model.camera('cam').id]))

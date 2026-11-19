"""仅在保存点云上核验全场景体素网格变化，不修改过滤实现。"""
import json
from pathlib import Path
import numpy as np
import open3d as o3d
from grasp_process import ModelFreeCollisionDetector
from geometry.candidates import original

OUT = Path('/home/yeliheng/grasp_server/geometry_20261019')
VOXEL = .008
LOCAL_RADIUS = .12


def sort_rows(points):
    return points[np.lexsort(points.T[::-1])]


def anchored(points, low, high):
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    result, _, _ = cloud.voxel_down_sample_and_trace(VOXEL, low, high)
    return np.asarray(result.points)


def metrics(detector, group):
    c, e, parts = detector.detect(group, approach_dist=.06, collision_thresh=.01,
        return_empty_grasp=True, empty_thresh=.003, return_ious=True)
    return {'collision': c.tolist(), 'empty': e.tolist(), 'ious': [p.tolist() for p in parts]}


def inspect(source):
    plain = np.load(OUT / f'{source}-none.npz')
    fault = np.load(OUT / f'{source}-collision.npz')
    center = np.median(plain['target'], axis=0)
    local = [sort_rows(d['scene'][np.linalg.norm(d['scene']-center, axis=1) < LOCAL_RADIUS])
             for d in (plain, fault)]
    low = plain['scene'].min(axis=0)-VOXEL/2
    high = np.maximum(plain['scene'].max(axis=0), fault['scene'].max(axis=0))+VOXEL/2
    records = []
    for data in (plain, fault):
        detector = ModelFreeCollisionDetector(data['scene'], voxel_size=VOXEL)
        default_points = detector.scene_points
        record = {'default_grid_origin': (data['scene'].min(axis=0)-VOXEL/2).tolist(),
                  'default': metrics(detector, original(data['target']))}
        detector.scene_points = anchored(data['scene'], low, high)
        record['fixed_origin_diagnostic'] = metrics(detector, original(data['target']))
        record['default_equals_anchored'] = (default_points.shape == detector.scene_points.shape and
            bool(np.allclose(sort_rows(default_points), sort_rows(detector.scene_points), atol=1e-12, rtol=0)))
        records.append(record)
    return {'source': source, 'target_points_identical': bool(np.array_equal(plain['target'], fault['target'])),
            'local_radius_m': LOCAL_RADIUS, 'local_raw_counts': [len(p) for p in local],
            'local_raw_points_identical': bool(np.array_equal(*local)),
            'none_then_collision': records,
            'boundary': 'Fixed origin is diagnosis only; physical trials keep original detector'}


def main():
    result = [inspect(source) for source in ('GreenCylinder', 'OrangeSphere')]
    (OUT / 'voxel_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

"""先完整场景过滤，再去重和原目标约束排序。"""
import numpy as np
import grasp_process as grasp
from stability.proposals import filter_then_nms


def infer(color_path, depth_path, sam_mask_path=None, *, top_k=5, visualize=None,
          backend=None, fovy=np.pi/4):
    if backend != 'geometric':
        raise ValueError('独立实验仅支持geometric后端')
    _, target, scene, mask, depth = grasp.get_and_process_data(
        color_path, depth_path, sam_mask_path, fovy=fovy)
    points = np.asarray(target.points)
    candidates = grasp.generate_geometric_topdown_grasp(points)
    detector = grasp.ModelFreeCollisionDetector(np.asarray(scene.points), voxel_size=.008)
    safe = filter_then_nms(candidates, detector)
    ranked = grasp.rank_grasp_candidates(safe, points, mask, depth, fovy=fovy)
    selected = ranked[:max(1, min(int(top_k), len(ranked)))]
    return grasp.GraspGroup(np.stack([row[0].grasp_array for row in selected]))

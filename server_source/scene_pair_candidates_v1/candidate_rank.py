"""仅补救候选的俯视角改用世界竖直基准，其他排序约束不变。"""
import numpy as np
from grasp_process import GraspGroup
from world_candidates import DOWN_FRAME


def ranking(original, trace, camera):
    def rank(group, *args, **kwargs):
        if not trace.get('active'):
            return original(group, *args, **kwargs)
        rotation = np.asarray(camera['rotation']) @ DOWN_FRAME
        proxy = group.grasp_group_array.copy()
        transforms = proxy[:, 4:13].reshape(-1,3,3)
        proxy[:, 4:13] = (DOWN_FRAME @ rotation @ transforms).reshape(-1,9)
        proxy[:, -1] = np.arange(len(proxy))
        trace['ranking_angle_frame'] = 'world_down'
        rows = original(GraspGroup(proxy), *args, **kwargs)
        return [(group[int(g.object_id)], score, dict(info, angle_frame='world_down'))
                for g, score, info in rows]
    return rank

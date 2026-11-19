"""先登记全部10个动作，不按静态诊断筛掉失败项。"""
from pathlib import Path
from semanticfix2.design import items as previous_items,configuration
from posecheck.adapter import YAW_DEGREES

ROOT = Path('/home/yeliheng/grasp_server/descent_pose_v1')


def items():
    result = []
    for old in previous_items():
        if old['variant']!='lift45':
            continue
        for yaw in YAW_DEGREES:
            variant = 'lift45' if yaw==0 else f'yaw_{yaw}'
            result.append(dict(old,id=old['scene_id']+'_'+variant,variant=variant,yaw_deg=yaw))
    return result

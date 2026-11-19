"""先固定首两个安全抓姿，再独立枚举释放朝向与分支。"""
from itertools import product
import spatialmath as sm
from goal_policy import GRID,BOTTOM_GAPS_M
from ot_geometry import release_target
from ot_endpoints import YAWS

PITCHES=(0.,15.,-15.,30.,-30.)
CONFIGS=tuple(product((1,-1),repeat=3))
MAX_GRASP_POSES=2


def first_poses(grasps):
    rows,seen=[],set()
    for row in grasps:
        if row['pose'] in seen:
            continue
        rows.append(row)
        seen.add(row['pose'])
        if len(rows)==MAX_GRASP_POSES:
            break
    return rows


def candidates(grasps, poses, *, points, dimensions):
    selected=first_poses(grasps)
    for grid,gap,yaw,pitch,config,row in product(GRID,BOTTOM_GAPS_M,YAWS,PITCHES,CONFIGS,selected):
        grasp=poses[row['pose']]
        rotation=sm.SO3.Rz(yaw,unit='deg').R@grasp.R@sm.SO3.Ry(pitch,unit='deg').R
        try:
            release=release_target(grasp,rotation,points=points,dimensions=dimensions,grid=grid,gap=gap)
        except ValueError as error:
            assert str(error)=='Rotated volume does not fit registered margin'
            continue
        yield dict(grasp=row,yaw=yaw,pitch=pitch,config=list(config),grid=list(grid),gap=gap,release=release)

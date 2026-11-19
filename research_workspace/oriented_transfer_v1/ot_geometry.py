"""在TCP坐标变换下计算持物保守体积及合法释放目标。"""
import numpy as np
import spatialmath as sm
from goal_policy import EDGE_MARGIN_M


def moved(points, grasp, release):
    points=np.asarray(points,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)==0 or not np.isfinite(points).all():
        raise ValueError('Finite nonempty Nx3 volume required')
    rotation=release.R@grasp.R.T
    return (points-grasp.t)@rotation.T+release.t


def release_target(grasp, rotation, *, points, dimensions, grid, gap):
    offset=moved(points,grasp,sm.SE3.Rt(rotation,[0.,0.,0.]))
    low,high=np.min(offset,axis=0),np.max(offset,axis=0)
    half=(high-low)/2
    usable=np.asarray(dimensions['interior_half'])-half[:2]-EDGE_MARGIN_M
    if np.min(usable)<=0 or gap<=0 or not np.isfinite(gap):
        raise ValueError('Rotated volume does not fit registered margin')
    center=np.asarray(dimensions['bin_center'],dtype=float).copy()
    center[:2]+=np.asarray(grid)*usable
    center[2]=dimensions['wall_top']+gap+half[2]
    return sm.SE3.Rt(rotation,center-(low+high)/2)

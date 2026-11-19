"""持物旋转几何（RED接口）。"""
import numpy as np
import spatialmath as sm


def moved(points, grasp, release):
    return np.asarray(points)+release.t-grasp.t


def release_target(grasp, rotation, *, points, dimensions, grid, gap):
    center=np.asarray(dimensions['bin_center'],dtype=float).copy()
    half=(np.max(points,axis=0)-np.min(points,axis=0))/2
    center[:2]+=np.asarray(grid)*(np.asarray(dimensions['interior_half'])-half[:2]-.020)
    center[2]=dimensions['wall_top']+gap+half[2]
    return sm.SE3.Rt(rotation,center)

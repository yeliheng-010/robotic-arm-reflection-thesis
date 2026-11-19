"""持物体积接口（RED）。"""
import numpy as np
import mujoco


def body_pose(model, data, source):
    import spatialmath as sm
    body=data.body(source)
    return sm.SE3.Rt(body.xmat.reshape(3,3),body.xpos.copy())


def place(model, data, *, source, initial, grasp, release):
    pass


def collisions(model, data, source):
    return []


def corners(model, data, source):
    return np.zeros((8,3))

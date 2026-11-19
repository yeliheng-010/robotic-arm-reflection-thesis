"""固定姿态候选与反馈门控；不使用案例编号或未来成败。"""
import numpy as np
import spatialmath as sm

YAW_OFFSETS = (0,180,90,-90,45,-45,135,-135)


def poses(nominal):
    closing = nominal.R[:,1].copy()
    closing[2] = 0
    if np.linalg.norm(closing)<1e-9:
        closing = np.array([0.,1.,0.])
    closing /= np.linalg.norm(closing)
    rows = [dict(id='original',pose=nominal.copy())]
    for yaw in YAW_OFFSETS:
        axis = sm.SO3.Rz(yaw,unit='deg').R@closing
        rotation = sm.SO3.TwoVectors(x=[0.,0.,-1.],y=axis)
        rows.append(dict(id=f'world_down_{yaw}',pose=sm.SE3.Rt(rotation,nominal.t)))
    return rows


def eligible(report):
    if report is None:
        return False
    phase = report.get('evidence',{}).get('motion_context',{}).get('phase')
    return (report['error_type'],phase) in {
        ('collision','grasp_pose'),('collision','grasp_approach'),('ik_failure','carry_transport')}


def select(rows):
    return next((i for i,row in enumerate(rows) if row['feasible']),None)

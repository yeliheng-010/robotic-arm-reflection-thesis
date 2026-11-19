"""原范围内局部相机候选与只改变朝向的抓取候选。"""
from itertools import product
import numpy as np
import spatialmath as sm
from sd_camera import look_at, BASE_POSITION, TARGET

LIMIT = 128
ANGLES = (15., -15., 30., -30.)
BASE_GRASPS = 16
CAMERA_STEPS = ((0,5.),(0,-5.),(0,10.),(0,-10.),(1,2.),(1,-2.),(1,5.),(1,-5.),
    (2,.04),(2,-.04),(3,2.),(3,-2.),(4,.03),(4,-.03),(5,.03),(5,-.03))


def camera_key(camera):
    values = [*camera['position'], *camera['target'], camera['fovy']]
    return tuple(np.round(values, 12))


def offsets():
    for index, step in CAMERA_STEPS:
        row = np.zeros(6)
        row[index] = step
        yield row
    for azimuth, elevation, distance in product((-10.,10.),(-4.,4.),(-.05,.05)):
        yield np.array([azimuth,elevation,distance,0.,0.,0.])


def changed(anchor, delta, center):
    value = np.array([anchor['azimuth_offset_deg'],anchor['elevation_deg'],
        anchor['distance_m'],anchor['fovy'],*anchor['target'][:2]]) + delta
    scale = np.linalg.norm(BASE_POSITION-TARGET)
    low = np.array([-60.,35.,.8*scale,48.,center[0]-.1,center[1]-.1])
    high = np.array([60.,75.,1.3*scale,65.,center[0]+.1,center[1]+.1])
    if not np.isfinite(value).all() or np.any(value<low) or np.any(value>high):
        return None
    azimuth, elevation = np.deg2rad([180.+value[0],value[1]])
    target = np.array([*value[4:],anchor['target'][2]])
    direction = np.array([np.cos(elevation)*np.cos(azimuth),
        np.cos(elevation)*np.sin(azimuth),np.sin(elevation)])
    position = target+value[2]*direction
    return dict(position=position.tolist(),target=target.tolist(),rotation=look_at(position,target).tolist(),
        fovy=float(value[3]),azimuth_offset_deg=float(value[0]),elevation_deg=float(value[1]),distance_m=float(value[2]))


def cameras(anchors, boxes, *, previous):
    bounds = np.asarray(list(boxes.values()))
    center = (bounds[:,0].min(axis=0)+bounds[:,1].max(axis=0))/2
    seen, rows = {camera_key(row) for row in previous}, []
    for delta, anchor in product(offsets(), anchors[:3]):
        camera = changed(anchor, delta, center)
        if camera is None:
            continue
        key = camera_key(camera)
        if key in seen:
            continue
        rows.append(camera)
        seen.add(key)
        if len(rows) == LIMIT:
            break
    return rows


def grasps(nominal, fitted):
    from cp_candidates import candidates
    rows = []
    for base, axis, angle in product(candidates(nominal,fitted)[:BASE_GRASPS],('y','z'),ANGLES):
        rotation = sm.SO3.Ry(angle,unit='deg') if axis=='y' else sm.SO3.Rz(angle,unit='deg')
        pose = sm.SE3.Rt(base['pose'].R@rotation.R,base['pose'].t)
        rows.append(dict(id=base['id']+f'_tilt_{axis}_{angle}',pose=pose,axis=axis,angle_deg=angle))
    assert len(rows) <= LIMIT
    return rows

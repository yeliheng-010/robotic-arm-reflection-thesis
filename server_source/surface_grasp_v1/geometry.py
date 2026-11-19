"""可见表面与朝向构造。"""
import numpy as np

ANCHORS, NEIGHBOURS = 12,64
TRIM = (2,98)
ROLLS = tuple(range(0,360,30))
EPSILON = 1e-10


def cloud(value, minimum=64):
    points=np.asarray(value,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<minimum or not np.isfinite(points).all():
        raise ValueError('Finite Nx3 observed points required')
    return points[np.lexsort((points[:,2],points[:,1],points[:,0]))]


def unit(value):
    value=np.asarray(value,dtype=float)
    length=np.linalg.norm(value)
    if not np.isfinite(value).all() or length<EPSILON:
        raise ValueError('Invalid direction')
    return value/length


def local_surface(points, selected, camera):
    order=np.argsort(np.linalg.norm(points-selected,axis=1),kind='stable')[:NEIGHBOURS]
    local=points[order]
    point=np.median(local,axis=0)
    values,vectors=np.linalg.eigh(np.cov(local.T))
    if values[1]<EPSILON:
        raise ValueError('Degenerate local surface')
    normal=vectors[:,0]
    if np.dot(normal,camera-point)<0:
        normal=-normal
    return dict(point=point.tolist(),normal=normal.tolist(),support=len(local))


def anchors(points, camera):
    points=cloud(points)
    camera=np.asarray(camera,dtype=float)
    if camera.shape!=(3,) or not np.isfinite(camera).all():
        raise ValueError('Finite calibrated camera required')
    low,high=np.percentile(points,TRIM,axis=0)
    robust=points[np.all((points>=low)&(points<=high),axis=1)]
    if len(robust)<NEIGHBOURS:
        raise ValueError('Insufficient robust surface')
    chosen=int(np.argmin(np.linalg.norm(robust-np.median(robust,axis=0),axis=1)))
    distances=np.full(len(robust),np.inf)
    rows=[]
    for index in range(ANCHORS):
        rows.append(dict(id=f'anchor_{index:02d}',**local_surface(points,robust[chosen],camera)))
        distances=np.minimum(distances,np.linalg.norm(robust-robust[chosen],axis=1))
        chosen=int(np.argmax(distances))
    return rows


def approaches(normal, long_axis):
    long=unit([*long_axis[:2],0.])
    vertical=np.array([0.,0.,-1.])
    slope=np.deg2rad(60.)
    return [('normal',-unit(normal)),('vertical',vertical),
            ('slant_positive',np.sin(slope)*long+np.cos(slope)*vertical),
            ('slant_negative',-np.sin(slope)*long+np.cos(slope)*vertical),
            ('side_positive',long),('side_negative',-long)]


def orientations(normal, long_axis):
    rows=[]
    for family,approach in approaches(normal,long_axis):
        seed=np.eye(3)[int(np.argmin(np.abs(approach)))]
        base=unit(seed-np.dot(seed,approach)*approach)
        perpendicular=np.cross(approach,base)
        for degree in ROLLS:
            angle=np.deg2rad(degree)
            closing=np.cos(angle)*base+np.sin(angle)*perpendicular
            basis=np.column_stack((approach,closing,np.cross(approach,closing)))
            rows.append(dict(family=family,roll_deg=degree,rotation=basis.tolist()))
    return rows

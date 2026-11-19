"""胶囊形状先验的部分表面拟合；不接受仿真物体位姿。"""
import numpy as np

MIN_POINTS=128
MAX_POINTS=768
MAX_RESIDUAL_M=.006
MAX_CENTER_DISAGREEMENT_M=.010
MAX_AXIS_DISAGREEMENT_DEG=12.
MIN_VARIANCE=1e-7


def sample(value):
    points=np.asarray(value,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<MIN_POINTS or not np.isfinite(points).all():
        raise ValueError('insufficient_or_nonfinite_points')
    order=np.lexsort((points[:,2],points[:,1],points[:,0]))
    indices=np.linspace(0,len(points)-1,min(MAX_POINTS,len(points)),dtype=int)
    return points[order[indices]]


def direction(params,basis):
    vector=basis[:,0]+params[3]*basis[:,1]+params[4]*basis[:,2]
    return vector/np.linalg.norm(vector)


def residual(params,points,basis):
    axis=direction(params,basis)
    relative=points-params[:3]
    distance=np.clip(relative@axis,-params[6],params[6])
    return np.linalg.norm(relative-distance[:,None]*axis,axis=1)-params[5]


def fit(points):
    from scipy.optimize import least_squares
    center=np.median(points,axis=0)
    values,basis=np.linalg.eigh(np.cov(points.T))
    if values[0]<MIN_VARIANCE:
        raise ValueError('degenerate_surface')
    basis=basis[:,::-1]
    relative=points-center
    radius=float(np.clip(np.percentile(np.linalg.norm(relative@basis[:,1:],axis=1),40),.010,.045))
    extent=np.ptp(np.percentile(relative@basis[:,0],[5,95]))
    half=float(np.clip(extent/2-radius/2,.025,.12))
    low=[*(points.min(axis=0)-.10),-2.,-2.,.006,.015]
    high=[*(points.max(axis=0)+.10),2.,2.,.080,.150]
    trials=[]
    shifts=[np.zeros(3),radius*basis[:,1]/2,-radius*basis[:,1]/2,
            radius*basis[:,2]/2,-radius*basis[:,2]/2]
    for shift in shifts:
        initial=[*(center+shift),0.,0.,radius,half]
        result=least_squares(residual,initial,args=(points,basis),bounds=(low,high),
            loss='soft_l1',f_scale=.003,max_nfev=150)
        trials.append(result)
    best=min(trials,key=lambda row:row.cost)
    p=best.x
    errors=np.abs(residual(p,points,basis))
    singular=np.linalg.svd(best.jac,compute_uv=False)
    return dict(center=p[:3].tolist(),axis=direction(p,basis).tolist(),radius=float(p[5]),
        half_length=float(p[6]),p95_m=float(np.percentile(errors,95)),
        converged=bool(best.success),condition=float(singular[0]/max(singular[-1],1e-15)))


def consistency(fits):
    combined=fits[0]
    centers=[np.linalg.norm(np.asarray(row['center'])-combined['center']) for row in fits[1:]]
    angles=[np.rad2deg(np.arccos(np.clip(abs(np.dot(row['axis'],combined['axis'])),0.,1.))) for row in fits[1:]]
    passed=all(row['converged'] and row['p95_m']<=MAX_RESIDUAL_M and row['condition']<1e4
               and row['half_length']>=row['radius'] for row in fits)
    passed=passed and max(centers)<=MAX_CENTER_DISAGREEMENT_M and max(angles)<=MAX_AXIS_DISAGREEMENT_DEG
    return dict(passed=bool(passed),max_center_disagreement_m=float(max(centers)),
        max_axis_disagreement_deg=float(max(angles)),fits=fits,
        confidence_kind='registered_fit_consistency_not_calibrated_probability')


def estimate(views,tcp):
    base=dict(quality_passed=False,release_authorized=False,roll_observable=False,
        prior='capsule',perception='simulation_assisted_segmentation_noisy_rgbd')
    if len(views)!=2:
        return dict(base,reason='two_qualified_distinct_views_required')
    try:
        points=[sample(view) for view in views]
        pose=np.asarray(tcp,dtype=float)
        if pose.shape!=(4,4) or not np.isfinite(pose).all():
            raise ValueError('invalid_tcp')
        np.testing.assert_allclose(pose[:3,:3].T@pose[:3,:3],np.eye(3),atol=1e-8)
        fits=[fit(sample(np.vstack(points)))]+[fit(p) for p in points]
        quality=consistency(fits)
    except (ValueError,AssertionError) as error:
        return dict(base,reason=str(error))
    if not quality['passed']:
        return dict(base,reason='fit_consistency_rejected',quality=quality)
    center=np.asarray(fits[0]['center'])
    axis=np.asarray(fits[0]['axis'])
    return dict(base,quality_passed=True,center_world_m=center.tolist(),axis_world=axis.tolist(),
        center_tcp_m=(pose[:3,:3].T@(center-pose[:3,3])).tolist(),
        axis_tcp=(pose[:3,:3].T@axis).tolist(),quality=quality)

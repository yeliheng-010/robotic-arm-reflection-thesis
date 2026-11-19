"""有限候选与可见邻域排序。"""
from collections import Counter,defaultdict
from itertools import product
import numpy as np
from observed_top_pose_v1.top_fit import estimate
from natural_grasp_span_audit_v1.span import span
from model_grasp_intent_v1.geometry import MAX_TRANSLATION_M, MAX_WIDTH_M, WIDTH_MARGIN_M
from surface_grasp_v1.geometry import anchors,orientations,cloud

DEPTHS_M=(.005,.010,.020)
MAX_CANDIDATES=512
VOXEL_M=.010
SCENE_LIMIT=4096
BACKOFF_M=(.025,.050,.075,.100)


def key(pose):
    return tuple(np.round(np.asarray(pose).ravel(),12))


def scene_sample(scene):
    points=cloud(scene,minimum=1)
    _,indices=np.unique(np.floor(points/VOXEL_M),axis=0,return_index=True)
    sampled=points[np.sort(indices)]
    take=np.linspace(0,len(sampled)-1,min(SCENE_LIMIT,len(sampled)),dtype=int)
    return sampled[take]


def proxy_distance(scene, pose):
    probes=pose[:3,3]-np.array(BACKOFF_M)[:,None]*pose[:3,0]
    return float(np.min(np.linalg.norm(scene[:,None,:]-probes[None,:,:],axis=2)))


def proposal(points, anchor, *, orientation, depth, nominal):
    basis=np.asarray(orientation['rotation'])
    center=np.asarray(anchor['point'])+depth*basis[:,0]
    if np.linalg.norm(center-nominal)>MAX_TRANSLATION_M:
        return dict(status='rejected',reason='translation_limit')
    low,high=np.percentile((points-center)@basis[:,1],[5,95])
    width=max(span(points,basis[:,1]),2*max(abs(low),abs(high)))+WIDTH_MARGIN_M
    if width>MAX_WIDTH_M:
        return dict(status='rejected',reason='observed_span_or_centering')
    pose=np.eye(4)
    pose[:3,:3],pose[:3,3]=basis,center
    return dict(status='proposal',pose=pose.tolist(),required_width_m=width,full_path_verified=False)


def at_anchor(points, anchor, *, long_axis, nominal, scene, seen, counts):
    rows=[]
    for orientation,depth in product(orientations(anchor['normal'],long_axis),DEPTHS_M):
        candidate=proposal(points,anchor,orientation=orientation,depth=depth,nominal=nominal)
        counts['raw_proposals']+=1
        if candidate['status']!='proposal':
            counts[candidate['reason']]+=1
            continue
        identity=key(candidate['pose'])
        if identity in seen:
            counts['duplicates_or_previous']+=1
            continue
        seen.add(identity)
        rows.append(dict(anchor_id=anchor['id'],family=orientation['family'],
            roll_deg=orientation['roll_deg'],insertion_m=depth,proposal=candidate,
            observed_distance_proxy_m=proxy_distance(scene,np.asarray(candidate['pose']))))
    return rows


def balanced(rows):
    groups=defaultdict(list)
    for row in rows:
        groups[(row['anchor_id'],row['family'])].append(row)
    ranked=[sorted(group,key=lambda r:-r['observed_distance_proxy_m']) for group in groups.values()]
    chosen=[]
    for index in range(max((len(group) for group in ranked),default=0)):
        chosen.extend(group[index] for group in ranked if index<len(group))
    return chosen[:MAX_CANDIDATES]


def build(points, scene, *, nominal, camera, previous=()):
    points=cloud(points)
    nominal=np.asarray(nominal,dtype=float)
    if nominal.shape!=(3,) or not np.isfinite(nominal).all():
        raise ValueError('Finite nominal position required')
    fitted=estimate(points)
    if not fitted['available']:
        raise ValueError('Observed longitudinal reference unavailable')
    short=fitted['closing_axis']
    long_axis=[-short[1],short[0],0.]
    samples=anchors(points,camera)
    scene=scene_sample(scene)
    seen={key(pose) for pose in previous}
    counts,rows=Counter(),[]
    for anchor in samples:
        rows.extend(at_anchor(points,anchor,long_axis=long_axis,nominal=nominal,
                              scene=scene,seen=seen,counts=counts))
    selected=balanced(rows)
    catalogue=[dict(row,id=f'surface_{i:04d}') for i,row in enumerate(selected)]
    return dict(catalogue=catalogue,anchors=samples,summary=dict(counts,
        eligible_new_poses=len(rows),selected_poses=len(selected),scene_proxy_points=len(scene),
        ranking_only_not_safety=True,full_task_success=None))

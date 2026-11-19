"""不可变执行快照的合成重采样；真值仅进入审计记录。"""
from copy import deepcopy
import numpy as np

FIELDS=('grasp_residual_xy','placement_residual_xy')
NAMESPACE=941800
SIGMA=.005
CLIP=3.
OCCLUSION=.5
OUTLIER_PROBABILITY=.25
OUTLIER_METRES=.06
MODES={'occlusion':0,'outlier':1,'side_effect':2}


def relevant(feedback):
    error=feedback.get('error_type')
    if error in ('object_outside_container','placement_offset'):
        return 'placement_residual_xy'
    phase=feedback.get('evidence',{}).get('motion_context',{}).get('phase')
    if error in ('empty_grasp','object_dropped','ik_failure') and phase in ('grasp_approach','grasp_pose','carry_lift'):
        return 'grasp_residual_xy'
    return None


def sample(step,item,*,number):
    assert number in (0,1,2)
    value=deepcopy(step['feedback'])
    mode=item['mechanism']
    identity=[NAMESPACE,item['seed'],item['source']=='PurpleCapsule',MODES[mode],step['index'],number]
    audit={}
    for field_index,field in enumerate(FIELDS):
        if field not in value['evidence']:
            continue
        original=np.asarray(value['evidence'][field],dtype=float)
        assert original.shape==(2,) and np.isfinite(original).all()
        rng=np.random.default_rng(np.random.SeedSequence(identity+[field_index]))
        missing=bool(rng.random()<(OCCLUSION if mode=='occlusion' else 0.))
        delta=np.clip(rng.normal(size=2),-CLIP,CLIP)*SIGMA
        outlier=bool(rng.random()<(OUTLIER_PROBABILITY if mode=='outlier' else 0.))
        extra=rng.choice([-OUTLIER_METRES,OUTLIER_METRES],size=2) if outlier else np.zeros(2)
        audit[field]=dict(original=original.tolist(),missing=missing,delta=delta.tolist(),
                          outlier=outlier,outlier_delta=extra.tolist())
        if missing:
            del value['evidence'][field]
        else:
            value['evidence'][field]=(original+delta+extra).tolist()
    protocol=dict(mode='synthetic_snapshot_resampling',sigma_m=SIGMA,
        missing_probability=OCCLUSION if mode=='occlusion' else 0.,
        outlier_probability=OUTLIER_PROBABILITY if mode=='outlier' else 0.,
        outlier_m=OUTLIER_METRES if mode=='outlier' else 0.,labels='ideal_error_class_and_stage',units='metres')
    value['evidence']['measurement_protocol']=protocol
    value['evidence']['residual_corruption']=deepcopy(protocol)
    return dict(number=number,extra_cost=int(number>0),source_sha256=step['result_sha256'],
                state=deepcopy(step['state']),feedback=value,audit=audit,seed_components=identity)


def aggregate(samples,*,mode):
    assert samples and mode in ('latest','median')
    assert all(s['source_sha256']==samples[0]['source_sha256'] and s['state']==samples[0]['state'] for s in samples)
    value=deepcopy(samples[-1]['feedback'])
    if mode=='median':
        for field in FIELDS:
            values=[s['feedback']['evidence'][field] for s in samples if field in s['feedback']['evidence']]
            if values:
                value['evidence'][field]=np.median(np.asarray(values),axis=0).tolist()
    value['evidence']['observation_aggregation']=dict(mode=mode,count=len(samples),same_state=True)
    return value

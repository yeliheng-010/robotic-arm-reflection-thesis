"""同快照重采：缺失/离群只进审计，不向策略泄露。"""
from copy import deepcopy
import numpy as np
from sensor import aggregate

FIELDS=('grasp_residual_xy','placement_residual_xy')
NAMESPACE=942800
SIGMA=.005
MISSING=.35
OUTLIER=.25
OUTLIER_METRES=.06
CLIP=3.


def sample(step,item,*,number):
    assert number in (0,1,2)
    value=deepcopy(step['feedback'])
    identity=[NAMESPACE,item['seed'],int(item['source']=='PurpleCapsule'),item['factor_index'],step['index'],number]
    audits={}
    for i,field in enumerate(FIELDS):
        if field not in value['evidence']:
            continue
        truth=np.asarray(value['evidence'][field],dtype=float)
        assert truth.shape==(2,) and np.isfinite(truth).all()
        rng=np.random.default_rng(np.random.SeedSequence(identity+[i]))
        missing=bool(rng.random()<MISSING)
        delta=np.clip(rng.normal(size=2),-CLIP,CLIP)*SIGMA
        outlier=bool(rng.random()<OUTLIER)
        extra=rng.choice([-OUTLIER_METRES,OUTLIER_METRES],size=2) if outlier else np.zeros(2)
        audits[field]=dict(original=truth.tolist(),missing=missing,outlier=outlier,
                           delta=delta.tolist(),outlier_delta=extra.tolist())
        if missing:
            del value['evidence'][field]
        else:
            value['evidence'][field]=(truth+delta+extra).tolist()
    protocol=dict(mode='synthetic_snapshot_resampling',sigma_m=SIGMA,missing_probability=MISSING,
        outlier_probability=OUTLIER,outlier_m=OUTLIER_METRES,labels='ideal_error_class_and_stage',units='metres')
    value['evidence']['measurement_protocol']=protocol
    value['evidence']['residual_corruption']=deepcopy(protocol)
    return dict(number=number,extra_cost=int(number>0),source_sha256=step['result_sha256'],
        state=deepcopy(step['state']),feedback=value,audit=audits,seed_components=identity)

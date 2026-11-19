"""仅扰动残差测量，原值只写审计侧，不提供给模型。"""
from copy import deepcopy
import numpy as np

FIELDS = ('grasp_residual_xy','placement_residual_xy')
SIGMAS = (0.,.005,.015)
MISSING = (0.,.25)
CLIP = 3.


def profiles():
    return [dict(sigma_m=s,missing_probability=p) for s in SIGMAS for p in MISSING]


def project(report,profile,*,seed):
    if profile not in profiles():
        raise ValueError('Unregistered feedback profile')
    value,audit = deepcopy(report),{}
    for index,field in enumerate(FIELDS):
        if field not in value['evidence']:
            continue
        original=np.asarray(value['evidence'][field],dtype=float)
        if original.shape!=(2,) or not np.isfinite(original).all():
            raise ValueError('Invalid residual')
        rng=np.random.default_rng(np.random.SeedSequence([seed,index]))
        missing=bool(rng.random()<profile['missing_probability'])
        delta=np.clip(rng.normal(size=2),-CLIP,CLIP)*profile['sigma_m']
        audit[field]=dict(original=original.tolist(),missing=missing,delta=delta.tolist())
        if missing:
            del value['evidence'][field]
        else:
            value['evidence'][field]=(original+delta).tolist()
    value['evidence']['residual_corruption']=dict(profile,fields=list(FIELDS),clip_sigma=CLIP,
        source='synthetic_residual_feedback_only',stage_and_contact_geometry='ideal_unchanged')
    value['evidence']['measurement_protocol']=dict(mode='synthetic_residual_feedback',
        residual_sigma_m=profile['sigma_m'],residual_missing_probability=profile['missing_probability'],
        affected_fields=list(FIELDS),labels='ideal_error_class_and_stage',units='metres',input='text_only')
    return value,audit

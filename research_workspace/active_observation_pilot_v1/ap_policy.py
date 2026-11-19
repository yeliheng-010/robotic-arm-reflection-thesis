"""用可见测量一致性分配观测预算；不是校准过的概率置信度。"""
from math import dist
from itertools import combinations
from loopstudy.actions import candidates,choose_rule
from ap_common import METHODS,MAX_EXTRA
from ap_sensor import sample,aggregate,FIELDS

CONSISTENCY_METRES=.03
GRASP_PHASES=('grasp_approach','grasp_pose','carry_lift','carry_transport','place_descent')


def targets(samples):
    feedback=samples[0]['feedback']
    error=feedback['error_type']
    if error in ('object_outside_container','placement_offset'):
        return ['placement_residual_xy']
    visible=[f for f in FIELDS if any(f in s['feedback']['evidence'] for s in samples)]
    if visible:
        return visible
    phase=feedback['evidence'].get('motion_context',{}).get('phase')
    if error in ('empty_grasp','object_dropped','ik_failure') and phase in GRASP_PHASES:
        return ['grasp_residual_xy']
    return []


def quality(samples):
    assert samples
    assert all(s['source_sha256']==samples[0]['source_sha256'] and s['state']==samples[0]['state'] for s in samples)
    out={}
    for field in targets(samples):
        values=[s['feedback']['evidence'][field] for s in samples if field in s['feedback']['evidence']]
        spread=max((dist(a,b) for a,b in combinations(values,2)),default=0.)
        status='missing' if not values else 'unconfirmed' if len(values)==1 else 'conflict' if spread>CONSISTENCY_METRES else 'consistent'
        out[field]=dict(visible_count=len(values),spread_m=spread,status=status)
    return out


def observe(step,item,*,method,used):
    assert method in METHODS and 0<=used<=MAX_EXTRA
    samples=[sample(step,item,number=0)]
    events=[]
    while used+len(samples)-1<MAX_EXTRA:
        q=quality(samples)
        uncertain=any(v['status']!='consistent' for v in q.values())
        request=used==0 if method=='fixed_first' else uncertain
        if not request:
            break
        events.append(dict(number=len(samples),reason='fixed_first' if method=='fixed_first' else 'visible_uncertainty',quality_before=q))
        samples.append(sample(step,item,number=len(samples)))
    return dict(samples=samples,extra_cost=len(samples)-1,events=events,
        initial_quality=quality(samples[:1]),final_quality=quality(samples),feedback=aggregate(samples,mode='median'))


def decide(step,observation):
    feedback,state=observation['feedback'],step['state']
    rows=candidates(feedback,state,[],legacy=False)
    selected=choose_rule(rows,state,report=feedback) if rows else None
    return dict(after_attempt=step['index'],before=state,feedback=feedback,candidates=rows,
        selected=selected,observation=observation,model=None,source='visible_feedback_rule')

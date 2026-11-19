"""预登记规则只读取可见反馈；额外观测不占物理尝试。"""
from loopstudy.actions import candidates,choose_rule
from sensor import sample,relevant,aggregate
from pilot import MAX_EXTRA


def modes(item):
    return {'occlusion':('no_extra','reobserve'),'outlier':('latest','median'),
            'side_effect':('rule',)}[item['mechanism']]


def observe(step,item,*,mode,used):
    assert 0<=used<=MAX_EXTRA and mode in modes(item)
    samples=[sample(step,item,number=0)]
    target=relevant(samples[0]['feedback'])
    if item['mechanism']=='outlier' and used==0:
        samples.extend(sample(step,item,number=n) for n in (1,2))
    elif mode=='reobserve' and target:
        while len(samples)-1<MAX_EXTRA-used and target not in samples[-1]['feedback']['evidence']:
            samples.append(sample(step,item,number=len(samples)))
    cost=len(samples)-1
    assert used+cost<=MAX_EXTRA
    effective=aggregate(samples,mode='median' if mode=='median' else 'latest')
    return dict(samples=samples,extra_cost=cost,feedback=effective,target_field=target)


def decide(step,observation,*,alternate=None):
    feedback,state=observation['feedback'],step['state']
    rows=candidates(feedback,state,[],legacy=False)
    selected=choose_rule(rows,state,report=feedback) if rows else None
    if alternate is not None:
        assert alternate in rows and alternate['kind']=='descent_route'
        selected=alternate
    return dict(after_attempt=step['index'],before=state,feedback=feedback,candidates=rows,selected=selected,
                observation=observation,source='qualified_route_branch' if alternate else 'visible_feedback_rule',model=None)


def branch_target(trace):
    for index,d in enumerate(trace['decisions']):
        if d['selected'] and d['selected']['kind']=='descent_route':
            others=[r for r in d['candidates'] if r['kind']=='descent_route' and r!=d['selected']]
            if others:
                return index,sorted(others,key=lambda r:r['id'])[0]
    return None

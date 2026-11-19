"""三次执行策略的累计成功与费用；不伪称不同预算反事实。"""
from collections import Counter
from itertools import combinations
from am_common import METHODS


def trace_metrics(t):
    ds=t['decisions']
    events=[c['event'] for d in ds for c in d['choices'] if 'event' in c]
    return dict(success=t['success'],attempts=len(t['attempts']),extra_observations=t['extra_observations'],
        model_calls=len(events),invalid=sum(bool(d['invalid']) for d in ds),
        prompt_tokens=sum(e['response']['usage']['prompt_tokens'] for e in events),
        completion_tokens=sum(e['response']['usage']['completion_tokens'] for e in events),
        model_seconds=sum(e['response']['elapsed_s'] for e in events),
        initially_failed=not t['attempts'][0]['success'],
        recovered=t['success'] and not t['attempts'][0]['success'],
        cumulative_success=[any(s['success'] for s in t['attempts'][:n]) for n in (1,2,3)],
        later_observation=sum(d['after_attempt']>1 and d['observation']['extra_cost']>0 for d in ds),
        missing=sum(any(v['status']=='missing' for v in d['observation']['initial_quality'].values()) for d in ds),
        visibility_recovered=sum(any(v['visible_count']==0 and d['observation']['final_quality'].get(f,{}).get('visible_count',0)>0
            for f,v in d['observation']['initial_quality'].items()) for d in ds))


def summarize(rows):
    active=[r for r in rows if r['eligible']]
    methods={}
    keys=('success','attempts','extra_observations','model_calls','invalid','prompt_tokens','completion_tokens',
          'model_seconds','initially_failed','recovered','later_observation','missing','visibility_recovered')
    for m in METHODS:
        values=[r['methods'][m] for r in active]
        methods[m]=dict(executed=len(values),**{k:sum(v[k] for v in values) for k in keys},
            cumulative_success=[sum(v['cumulative_success'][i] for v in values) for i in range(3)])
    pairs={}
    for a,b in combinations(METHODS,2):
        c=Counter()
        for r in active:
            x,y=(r['methods'][m]['success'] for m in (a,b))
            c['both_success' if x and y else 'a_only' if x else 'b_only' if y else 'both_fail']+=1
        pairs[a+'__'+b]=dict(c)
    return dict(planned=len(rows),eligible=len(active),skipped=len(rows)-len(active),methods=methods,paired=pairs)


def analyze(values,reader):
    rows=[]
    for v in values:
        traces={p.split('/')[-2]:reader(p) for p in v['trajectories']}
        assert set(traces)==(set(METHODS) if v['eligible'] else set())
        rows.append(dict(id=v['scene']['id'],seed=v['scene']['seed'],factor=v['scene']['factor'],
            eligible=v['eligible'],methods={m:trace_metrics(t) for m,t in traces.items()}))
    seeds=sorted({r['seed'] for r in rows})
    return dict(rows=rows,overall=summarize(rows),seed_groups=len(seeds),
        by_seed={str(s):summarize([r for r in rows if r['seed']==s]) for s in seeds},
        by_factor={f:summarize([r for r in rows if r['factor']==f]) for f in sorted({r['factor'] for r in rows})},
        primary_execution_budget=3,prefixes_are_counterfactual_budgets=False)

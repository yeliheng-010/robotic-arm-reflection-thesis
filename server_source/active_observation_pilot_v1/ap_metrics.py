"""完整预算曲线和真实信息暴露，观察次数与物理次数分别计费。"""
from collections import Counter
from ap_common import METHODS


def prefix(trace,budget):
    steps=trace['attempts'][:budget]
    ds=[d for d in trace['decisions'] if d['after_attempt']<budget]
    return dict(success=any(s['success'] for s in steps),first_success=steps[0]['success'],
        attempts=len(steps),extra_observations=sum(d['observation']['extra_cost'] for d in ds))


def curves(rows):
    active=[r for r in rows if r['eligible']]
    out=[]
    for budget in (1,2,3):
        methods={}
        for m in METHODS:
            values=[r['methods'][m][str(budget)] for r in active]
            methods[m]=dict(executed=len(values),successes=sum(v['success'] for v in values),
                attempts=sum(v['attempts'] for v in values),extra_observations=sum(v['extra_observations'] for v in values),
                initially_failed=sum(not v['first_success'] for v in values),
                recovered=sum(v['success'] and not v['first_success'] for v in values))
        paired=Counter()
        for r in active:
            a,b=(r['methods'][m][str(budget)]['success'] for m in METHODS)
            paired['both_success' if a and b else 'fixed_only' if a else 'adaptive_only' if b else 'both_fail']+=1
        out.append(dict(budget=budget,planned=len(rows),executed=len(active),skipped=len(rows)-len(active),methods=methods,paired=dict(paired)))
    return out


def exposure(trace):
    rows=[]
    for d in trace['decisions']:
        o=d['observation']
        states=[o['initial_quality'],o['final_quality']]+[e['quality_before'] for e in o['events']]
        missing=any(v['status']=='missing' for q in states for v in q.values())
        conflict=any(v['status']=='conflict' for q in states for v in q.values())
        recovered=any(v['visible_count']==0 and o['final_quality'].get(f,{}).get('visible_count',0)>0
                      for f,v in o['initial_quality'].items())
        rows.append(dict(after_attempt=d['after_attempt'],extra=o['extra_cost'],missing=missing,conflict=conflict,
            visibility_recovered=recovered,later_observation=d['after_attempt']>1 and o['extra_cost']>0,
            unresolved=any(v['status']!='consistent' for v in o['final_quality'].values()),
            selected_kind=d['selected']['kind'] if d['selected'] else None,
            phase=d['feedback']['evidence'].get('motion_context',{}).get('phase')))
    return dict(method=trace['method'],success=trace['success'],attempts=len(trace['attempts']),rows=rows)


def analyze(values,reader):
    rows,details=[],[]
    for value in values:
        traces={p.split('/')[-2]:reader(p) for p in value['trajectories']}
        assert set(traces)==(set(METHODS) if value['eligible'] else set())
        rows.append(dict(id=value['scene']['id'],seed=value['scene']['seed'],factor=value['scene']['factor'],
            eligible=value['eligible'],methods={m:{str(b):prefix(t,b) for b in (1,2,3)} for m,t in traces.items()}))
        details.extend(dict(id=value['scene']['id'],**exposure(t)) for t in traces.values())
    seeds=sorted({r['seed'] for r in rows})
    return dict(budgets=[1,2,3],shared_prefixes=True,post_hoc=False,seed_groups=len(seeds),
        rows=rows,curves=curves(rows),by_seed={str(s):curves([r for r in rows if r['seed']==s]) for s in seeds},
        by_factor={f:curves([r for r in rows if r['factor']==f]) for f in sorted({r['factor'] for r in rows})},
        exposure=details)

"""事前冻结的嵌套预算统计；不把前缀或跳过项算作独立执行。"""
from collections import Counter
from pathlib import Path

METHODS=('latest','median')
BUDGETS=(1,2,3)


def prefix(trace,budget):
    assert budget in BUDGETS
    steps=trace['attempts'][:budget]
    assert steps
    decisions=[d for d in trace['decisions'] if d['after_attempt']<budget]
    return dict(success=any(s['success'] for s in steps),first_success=steps[0]['success'],
        attempts=len(steps),extra_observations=sum(d['observation']['extra_cost'] for d in decisions))


def records(values,reader):
    output=[]
    for value in values:
        row=dict(id=value['scene']['id'],seed=value['scene']['seed'],source=value['scene']['source'],
                 eligible=value['eligible'],methods={})
        traces={Path(p).parent.name:reader(p) for p in value['trajectories']}
        assert set(traces)==(set(METHODS) if value['eligible'] else set())
        if traces:
            assert traces['latest']['attempts'][0]==traces['median']['attempts'][0]
            if traces['latest']['decisions']:
                assert traces['median']['decisions']
                a,b=(traces[m]['decisions'][0]['observation'] for m in METHODS)
                assert a['samples']==b['samples'] and a['extra_cost']==b['extra_cost']==2
        for method,trace in traces.items():
            row['methods'][method]={str(b):prefix(trace,b) for b in BUDGETS}
        output.append(row)
    return output


def summarize(rows):
    curves=[]
    for budget in BUDGETS:
        active=[r for r in rows if r['eligible']]
        methods={}
        for method in METHODS:
            data=[r['methods'][method][str(budget)] for r in active]
            methods[method]=dict(executed=len(data),successes=sum(r['success'] for r in data),
                first_success=sum(r['first_success'] for r in data),
                initially_failed=sum(not r['first_success'] for r in data),
                recovered=sum(r['success'] and not r['first_success'] for r in data),
                attempts=sum(r['attempts'] for r in data),
                extra_observations=sum(r['extra_observations'] for r in data))
        pairs=Counter()
        for r in active:
            a,b=(r['methods'][m][str(budget)]['success'] for m in METHODS)
            pairs['both_success' if a and b else 'latest_only' if a else 'median_only' if b else 'both_fail']+=1
        curves.append(dict(budget=budget,planned=len(rows),executed=len(active),skipped=len(rows)-len(active),
                           methods=methods,paired=dict(pairs)))
    return curves


def analyze(values,reader):
    rows=records(values,reader)
    seeds=sorted({r['seed'] for r in rows})
    return dict(preregistered_budgets=list(BUDGETS),independent_seed_groups=len(seeds),
        post_hoc=False,shared_prefixes=True,curves=summarize(rows),rows=rows,
        by_seed={str(s):summarize([r for r in rows if r['seed']==s]) for s in seeds})


def failures(values,reader):
    output=[]
    for value in values:
        for path in value['trajectories']:
            t=reader(path)
            if t['success']:
                continue
            output.append(dict(condition=value['scene']['id'],seed=value['scene']['seed'],mode=t['mode'],
                attempts=[dict(index=s['index'],success=s['success'],error=(s['feedback'] or {}).get('error_type'),
                    phase=(s['feedback'] or {}).get('evidence',{}).get('motion_context',{}).get('phase'))
                    for s in t['attempts']],
                choices=[dict(after_attempt=d['after_attempt'],selected=d['selected']) for d in t['decisions']]))
    return output

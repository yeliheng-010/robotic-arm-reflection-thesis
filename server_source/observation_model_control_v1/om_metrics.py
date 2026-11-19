"""四组嵌套预算、全部六配对、模型费用与种子组分母。"""
from collections import Counter
from itertools import combinations
from om_common import METHODS


def prefix(trace,budget):
    assert budget in (1,2,3)
    steps=trace['attempts'][:budget]
    decisions=[d for d in trace['decisions'] if d['after_attempt']<budget]
    events=[d['event'] for d in decisions if 'event' in d]
    usage=[e.get('response',{}).get('usage',{}) for e in events]
    return dict(success=any(s['success'] for s in steps),first_success=steps[0]['success'],
        attempts=len(steps),extra_observations=sum(d['observation']['extra_cost'] for d in decisions),
        model_calls=len(events),invalid=sum('invalid' in d for d in decisions),
        prompt_tokens=sum(u.get('prompt_tokens',0) for u in usage),
        completion_tokens=sum(u.get('completion_tokens',0) for u in usage),
        model_elapsed_s=sum(e['elapsed_s'] for e in events))


def curves(rows):
    active=[r for r in rows if r['eligible']]
    output=[]
    for budget in (1,2,3):
        methods={}
        for method in METHODS:
            data=[r['methods'][method][str(budget)] for r in active]
            total={k:sum(d[k] for d in data) for k in ('attempts','extra_observations','model_calls',
                   'invalid','prompt_tokens','completion_tokens','model_elapsed_s')}
            methods[method]=dict(total,executed=len(data),successes=sum(d['success'] for d in data),
                initially_failed=sum(not d['first_success'] for d in data),
                recovered=sum(d['success'] and not d['first_success'] for d in data))
        paired={}
        for a,b in combinations(METHODS,2):
            pairs=Counter()
            for r in active:
                x,y=(r['methods'][m][str(budget)]['success'] for m in (a,b))
                pairs['both_success' if x and y else 'left_only' if x else 'right_only' if y else 'both_fail']+=1
            paired[a+'__'+b]=dict(left=a,right=b,counts=dict(pairs))
        output.append(dict(budget=budget,planned=len(rows),executed=len(active),skipped=len(rows)-len(active),
                           methods=methods,paired=paired))
    return output


def analyze(values,reader):
    rows=[]
    for value in values:
        traces={p.split('/')[-2]:reader(p) for p in value['trajectories']}
        assert set(traces)==(set(METHODS) if value['eligible'] else set())
        rows.append(dict(id=value['scene']['id'],seed=value['scene']['seed'],eligible=value['eligible'],
            methods={m:{str(b):prefix(t,b) for b in (1,2,3)} for m,t in traces.items()}))
    seeds=sorted({r['seed'] for r in rows})
    return dict(budgets=[1,2,3],shared_prefixes=True,post_hoc=False,seed_groups=len(seeds),
        curves=curves(rows),rows=rows,by_seed={str(s):curves([r for r in rows if r['seed']==s]) for s in seeds})

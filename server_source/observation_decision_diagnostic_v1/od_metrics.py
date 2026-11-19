"""下一次重试的固定观测数配对；不解释为完整任务成功率。"""
from collections import Counter
from od_common import LEVELS,SELECTORS


def summarize(rows):
    arms={}
    for selector in SELECTORS:
        for level in LEVELS:
            values=[next(r for r in row['outcomes'] if r['selector']==selector and r['level']==level) for row in rows]
            arms[f'{selector}_l{level}']=dict(snapshots=len(values),successes=sum(v['success'] for v in values),
                executions=sum(v['attempted'] for v in values),extra_observations=sum(v['extra_observations'] for v in values))
    pairs={}
    for selector in SELECTORS:
        for level in LEVELS[1:]:
            counts=Counter()
            for row in rows:
                values={r['level']:r['success'] for r in row['outcomes'] if r['selector']==selector}
                a,b=values[0],values[level]
                counts['both_success' if a and b else 'direct_only' if a else 'observe_only' if b else 'both_fail']+=1
            pairs[f'{selector}_l0_vs_l{level}']=dict(counts)
    return dict(arms=arms,paired=pairs)


def analyze(values,summaries):
    rows=[]
    for value,summary in zip(values,summaries):
        case=value['case']
        rows.append(dict(summary,seed=case['seed'],scene_id=case['scene_id'],
            after_attempt=value['branches'][0]['source_index']))
    seeds=sorted({r['seed'] for r in rows})
    return dict(rows=rows,overall=summarize(rows),seed_groups=len(seeds),
        unique_conditions=len({r['scene_id'] for r in rows}),
        by_seed={str(s):summarize([r for r in rows if r['seed']==s]) for s in seeds},
        by_attempt={str(n):summarize([r for r in rows if r['after_attempt']==n]) for n in (1,2)})

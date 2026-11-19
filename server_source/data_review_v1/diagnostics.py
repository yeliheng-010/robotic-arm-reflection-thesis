"""描述冻结轨迹的失败与配对差异，不作未经执行的反事实归因。"""
from collections import Counter, defaultdict


def error_of(step):
    return (step['feedback'] or {}).get('error_type','success')


def trace(result):
    item = result['item']
    return dict(task_id=item['id'], arm=item['arm'], seed=item['seed'],
                factor=item['factor'], source=item['source'], split=item['split'],
                success=result['success'], status=result['status'],
                attempts=len(result['attempts']),
                errors=[error_of(s) for s in result['attempts']],
                phases=[(s['feedback'] or {}).get('phase') for s in result['attempts']],
                choices=[d['selected']['id'] if d['selected'] else None for d in result['decisions']],
                candidate_counts=[len(d['candidates']) for d in result['decisions']])


def hard_diagnostics(results):
    traces = [trace(r) for r in results]
    by_pair = defaultdict(dict)
    for result in results:
        by_pair[result['item']['pair_id']][result['item']['arm']] = result
    outcomes, disagree = Counter(), []
    for key, pair in by_pair.items():
        rule, hybrid = pair['new_rule'], pair['hybrid']
        outcome = ('both_success' if rule['success'] and hybrid['success'] else
                   'rule_only' if rule['success'] else
                   'hybrid_only' if hybrid['success'] else 'both_fail')
        outcomes[outcome] += 1
        if outcome in ('rule_only','hybrid_only'):
            disagree.append(dict(pair_id=key, outcome=outcome,
                                 rule=trace(rule), hybrid=trace(hybrid)))
    failures = [r for r in traces if not r['success']]
    sequences = Counter((r['factor'],r['arm'],' -> '.join(r['errors'])) for r in failures)
    budget = sum(r['attempts']==3 and r['status']=='completed' for r in failures)
    return dict(paired_outcomes=dict(outcomes), discordant_pairs=disagree,
                failed_tasks=len(failures), budget_exhausted=budget,
                failure_sequences=[dict(factor=k[0],arm=k[1],sequence=k[2],n=n)
                                   for k,n in sorted(sequences.items())], failures=failures,
                inference_limit='Observed trajectories only; candidate solvability not counterfactually tested')

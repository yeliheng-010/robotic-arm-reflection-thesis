"""只读测量与动作链：动作消费字段和阶段启发式分开报告。"""
from math import dist

METHODS=('latest','median')
CONSUMED={'measured_grasp':'grasp_residual_xy','measured_place':'placement_residual_xy'}
TOLERANCE=1e-12


def consumed_field(decision):
    selected=decision['selected']
    field=CONSUMED.get(selected['kind']) if selected else None
    if field:
        measurement=decision['feedback']['evidence'][field]
        assert selected['facts']['measurement']==measurement
    return field


def field_metrics(left,right,*,field):
    a,b=(d['observation'] for d in (left,right))
    assert a['samples']==b['samples']
    samples=a['samples']
    assert all(s['source_sha256']==samples[0]['source_sha256'] and
               s['state']==samples[0]['state'] for s in samples)
    truth=samples[0]['audit'][field]['original']
    assert all(s['audit'][field]['original']==truth for s in samples)
    errors={m:dist(d['feedback']['evidence'][field],truth) for m,d in zip(METHODS,(left,right))}
    delta=errors['median']-errors['latest']
    return dict(field=field,original_audit_only=truth,
        samples=[dict(number=s['number'],visible=s['feedback']['evidence'].get(field),
                      outlier_audit_only=s['audit'][field]['outlier']) for s in samples],
        effective={m:d['feedback']['evidence'][field] for m,d in zip(METHODS,(left,right))},
        errors_m=errors,median_error_change_m=delta,
        error_direction='lower' if delta < -TOLERANCE else 'higher' if delta > TOLERANCE else 'equal',
        last_sample_outlier=samples[-1]['audit'][field]['outlier'])


def outcomes(trace):
    return [dict(index=s['index'],success=s['success'],state=s['state'],
        error=(s['feedback'] or {}).get('error_type'),
        phase=(s['feedback'] or {}).get('evidence',{}).get('motion_context',{}).get('phase'))
        for s in trace['attempts']]


def initial_pair(traces):
    a,b=(traces[m] for m in METHODS)
    assert a['attempts'][0]==b['attempts'][0]
    if not a['decisions']:
        assert not b['decisions']
        return None
    left,right=(t['decisions'][0] for t in (a,b))
    assert left['before']==right['before'] and left['after_attempt']==right['after_attempt']==1
    assert left['observation']['samples']==right['observation']['samples']
    assert left['observation']['extra_cost']==right['observation']['extra_cost']==2
    fields=sorted(left['observation']['samples'][0]['audit'])
    consumed={m:consumed_field(d) for m,d in zip(METHODS,(left,right))}
    return dict(fields=[field_metrics(left,right,field=f) for f in fields],consumed_fields=consumed,
        heuristic_target=left['observation']['target_field'],
        selected={m:d['selected'] for m,d in zip(METHODS,(left,right))},
        candidates_equal=left['candidates']==right['candidates'],
        kinds={m:[c['kind'] for c in d['candidates']] for m,d in zip(METHODS,(left,right))})


def paired_budgets(traces):
    if not traces:
        return []
    result=[]
    for budget in (1,2,3):
        a,b=(any(s['success'] for s in traces[m]['attempts'][:budget]) for m in METHODS)
        result.append(dict(budget=budget,latest=a,median=b,
            paired='both_success' if a and b else 'latest_only' if a else 'median_only' if b else 'both_fail'))
    return result


def condition(value,reader):
    traces={p.split('/')[-2]:reader(p) for p in value['trajectories']}
    assert set(traces)==(set(METHODS) if value['eligible'] else set())
    return dict(id=value['scene']['id'],seed=value['scene']['seed'],eligible=value['eligible'],
        initial=initial_pair(traces) if traces else None,budgets=paired_budgets(traces),
        outcomes={m:outcomes(t) for m,t in traces.items()})

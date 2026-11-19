"""纯记录分析：当前输入相同不等于历史没有因果价值。"""
import json
from collections import Counter,defaultdict

RESIDUALS=('grasp_residual_xy','placement_residual_xy')


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False)


def prompt_parts(decision):
    messages=decision['event']['request']['messages']
    current=json.loads(messages[1]['content'])
    history=current.pop('history')
    return dict(system=messages[0]['content'],current=current),history


def compare_pair(left,right):
    counts=Counter()
    differences=[]
    counts['left_decisions']=len(left['decisions'])
    counts['right_decisions']=len(right['decisions'])
    for index,(a,b) in enumerate(zip(left['decisions'],right['decisions'])):
        x,no_history=prompt_parts(a)
        y,history=prompt_parts(b)
        assert no_history==[]
        assert len(history)==index
        same=x==y
        choice=a['selected']==b['selected']
        counts['paired_positions']+=1
        counts['nonempty_history_positions']+=bool(history)
        counts['same_current_input' if same else 'different_current_input']+=1
        counts['same_choice' if choice else 'different_choice']+=1
        if same:
            counts['same_input_same_choice' if choice else 'same_input_different_choice']+=1
            counts['same_input_with_history']+=bool(history)
            counts['same_input_same_text']+=a['event'].get('text')==b['event'].get('text')
        if not same or not choice:
            differences.append(dict(after_attempt=index+1,same_current_input=same,same_choice=choice,
                current=a['selected'],history=b['selected']))
    return dict(counts=dict(counts),differences=differences)


def feedback_context(feedback):
    f=feedback or {}
    evidence=f.get('evidence',{})
    return dict(error=f.get('error_type'),phase=evidence.get('motion_context',{}).get('phase'),
                residuals=[k for k in RESIDUALS if evidence.get(k) is not None])


def features(result,index,*,initial_state,rule_choice):
    d=result['decisions'][index]
    e=d['feedback'].get('evidence',{})
    history=result['decisions'][:index]
    rows=d['candidates']
    failed=[s['state'] for s in result['attempts'][:index] if not s['success']]
    measured=[c for c in rows if c['kind'].startswith('measured_')]
    selected=d['selected']
    missing=[k for k,a in result['attempts'][index].get('noise_audit',{}).items() if a['missing']]
    recoverable=[k for k in missing if any(h['feedback'].get('evidence',{}).get(k) is not None for h in history)]
    phase=e.get('motion_context',{}).get('phase')
    explicit_stage=(phase=='place_descent' and any(c['kind']=='descent_route' for c in rows)
        or phase=='carry_transport' and any(c['kind']=='exploratory_lift' for c in rows))
    return dict(after_attempt=index+1,history_nonempty=bool(history),candidates=len(rows),
        single_candidate=len(rows)==1,measured_candidates=len(measured),
        selected_kind=selected['kind'] if selected else None,
        selected_measured=bool(selected and selected['kind'].startswith('measured_')),
        agrees_with_rule=selected==rule_choice,current_state_nondefault=d['before']!=initial_state,
        ideal_error_stage=e.get('measurement_protocol',{}).get('labels')=='ideal_error_class_and_stage',
        measured_or_stage_specific_option=bool(measured or explicit_stage),
        past_failed_states_available=sum(c['state'] in failed for c in rows),
        selected_past_failed_state=bool(selected and selected['state'] in failed),
        missing_fields=missing,historical_visible_fields=recoverable,
        next_attempt_success=result['attempts'][index+1]['success'] if index+1<len(result['attempts']) else False,
        **feedback_context(d['feedback']))


def aggregate(rows):
    boolean=('history_nonempty','single_candidate','selected_measured','agrees_with_rule',
             'current_state_nondefault','ideal_error_stage','measured_or_stage_specific_option',
             'selected_past_failed_state','next_attempt_success')
    return dict(decisions=len(rows),**{k:sum(bool(r[k]) for r in rows) for k in boolean},
        measured_option=sum(r['measured_candidates']>0 for r in rows),
        missing_residual=sum(bool(r['missing_fields']) for r in rows),
        historical_measurement_available=sum(bool(r['historical_visible_fields']) for r in rows),
        past_failed_option_available=sum(r['past_failed_states_available']>0 for r in rows),
        candidate_counts=dict(Counter(r['candidates'] for r in rows)),
        choices=dict(Counter(r['selected_kind'] for r in rows)))


def history_opportunities(records):
    groups=defaultdict(list)
    for name,d in records:
        current,history=prompt_parts(d)
        groups[canonical(current)].append(dict(name=name,history=canonical(history),
                                              selected=canonical(d['selected'])))
    varied=[]
    for entries in groups.values():
        if len({e['history'] for e in entries})>1:
            varied.append(dict(records=[e['name'] for e in entries],histories=len({e['history'] for e in entries}),
                               choices=len({e['selected'] for e in entries})))
    return dict(records=len(records),unique_current_inputs=len(groups),
                same_current_different_history_groups=varied,
                note='Exact observed matches only; absence does not prove memory unnecessary')

"""区分同类动作与同参数动作，以及成功结果与决策一致。"""
import json
from collections import Counter
from loopstudy.actions import choose_rule


def same_input(left,right):
    return all(left[k]==right[k] for k in ('before','feedback','candidates'))


def feature(model,rule,*,next_success):
    rows=model['candidates']
    chosen=model['selected']
    measured=[r for r in rows if r['kind'].startswith('measured_')]
    payload=json.loads(model['event']['request']['messages'][1]['content'])
    assert payload['history']==[]
    return dict(same_input=same_input(model,rule),same_selected_action=chosen==rule['selected'],
        same_kind=chosen['kind']==rule['selected']['kind'],
        agrees_with_recomputed_rule=chosen==choose_rule(rows,model['before'],report=model['feedback']),
        candidates=len(rows),measured_candidates=len(measured),single_measured=len(measured)==1,
        selected_measured=chosen in measured,selected_kind=chosen['kind'],
        selected_position=rows.index(chosen),next_success=next_success,
        ideal_labels=model['feedback']['evidence']['measurement_protocol']['labels'],history_length=0)


def summarize(rows):
    keys=('same_input','same_selected_action','same_kind','agrees_with_recomputed_rule',
          'single_measured','selected_measured','next_success')
    return dict(decisions=len(rows),**{k:sum(r[k] for r in rows) for k in keys},
        candidate_counts=dict(Counter(r['candidates'] for r in rows)),
        selected_positions=dict(Counter(r['selected_position'] for r in rows)),
        selected_kinds=dict(Counter(r['selected_kind'] for r in rows)))

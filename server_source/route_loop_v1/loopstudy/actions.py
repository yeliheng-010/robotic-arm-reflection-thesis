"""候选只由可见反馈、参数、配置和历史构造。"""
import json
import random
from reflection.reflector import Parameters
from bounded.candidates import candidates as old_candidates,digest
from recovery.methods import choose_stage

PROFILES = {'original':0,'descent_minus45':-45,'descent_minus90':-90}


def canonical(value):
    return json.loads(json.dumps(value,ensure_ascii=False,allow_nan=False))


def initial():
    return canonical(dict(parameters=Parameters().to_dict(),profile='original'))


def validate(state):
    if set(state)!={'parameters','profile'} or state['profile'] not in PROFILES:
        raise ValueError('Invalid executor state')
    parameters = canonical(Parameters().updated(state['parameters']).to_dict())
    if parameters!=state['parameters']:
        raise ValueError('Incomplete or noncanonical parameters')
    return canonical(state)


def legacy_history(history):
    return [dict(reflection={'changes':r['selected']['changes']}) for r in history if r.get('selected')]


def legacy_rows(report,state,history):
    rows = old_candidates(report,state['parameters'],legacy_history(history))
    for row in rows:
        parameters = Parameters().updated(state['parameters']).updated(row['changes'])
        row['state'] = canonical(dict(parameters=parameters.to_dict(),profile=state['profile']))
    return rows


def route_rows(report,state):
    phase = report.get('evidence',{}).get('motion_context',{}).get('phase')
    if report['error_type']!='collision' or phase!='place_descent':
        return []
    rows = []
    for profile in ('descent_minus45','descent_minus90'):
        value = dict(state,profile=profile)
        rows.append(dict(kind='descent_route',changes={},state=value,
            explanation=f'执行配置切换为{profile}：运输保持原姿态，下降时绕世界Z轴旋转{PROFILES[profile]}度。',
            source='rule_generated_candidate',explanation_source='deterministic_action_template',
            facts=dict(yaw_deg=PROFILES[profile],timing='descent',assumption='Physical outcome not guaranteed')))
    return rows


def candidates(report,state,history,*,legacy=False):
    state = validate(state)
    rows = legacy_rows(report,state,history)
    if not legacy:
        rows += route_rows(report,state)
    seen = {digest(state)}|{digest(h['selected']['state']) for h in history if h.get('selected')}
    result = []
    for row in rows:
        value = validate(row['state'])
        key = digest(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(row,id='a_'+key[:12],state=value))
    random.Random(int(digest([r['id'] for r in result]),16)).shuffle(result)
    return canonical(result)


def choose_rule(rows,state,*,report,legacy=False):
    if not rows:
        raise ValueError('Candidate set exhausted')
    routes = [r for r in rows if r['kind']=='descent_route']
    phase = report.get('evidence',{}).get('motion_context',{}).get('phase')
    if not legacy and phase=='place_descent' and routes:
        return min(routes,key=lambda r:abs(PROFILES[r['state']['profile']]))
    return choose_stage(rows,Parameters().updated(state['parameters']),report=report)

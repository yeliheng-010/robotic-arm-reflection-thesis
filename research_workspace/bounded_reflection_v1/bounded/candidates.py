"""只从已展示测量生成合法候选；不读取场景名或故障真值。"""
import hashlib
import json
import math
import random
from reflection.reflector import Parameters, Reflection
from controlled.feedback import check_action

LIMIT = .25
DEPTH_STEP = .01
PROBE_STEP = .02
PRECISION = 9
PLACEMENT = ('placement_offset','object_outside_container')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def measured(parameters, evidence, *, field, key, kind):
    residual = evidence.get(key)
    if residual is None:
        return None
    if len(residual)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in residual):
        raise ValueError('Invalid measured residual')
    current = list(getattr(parameters,field))
    raw = [current[i]-residual[i] for i in range(2)]
    new = [round(max(-LIMIT,min(LIMIT,x)),PRECISION) for x in raw]+[current[2]]
    facts = dict(measurement=list(residual),current_value=current,new_value=new,
                 actual_delta=[round(new[i]-current[i],PRECISION) for i in range(3)],
                 saturated=[abs(x)>LIMIT for x in raw],units='metres')
    return dict(kind=kind,changes={field:new},facts=facts)


def exploration(parameters, changes, kind):
    field,new = next(iter(changes.items()))
    old = getattr(parameters,field)
    return dict(kind=kind,changes=changes,facts=dict(measurement=None,current_value=old,
                new_value=new,units='metres' if field.endswith('offset') or field=='lift_height' else 'native',
                assumption='Exploratory action; physical benefit unverified'))


def place_options(parameters, evidence):
    yield measured(parameters,evidence,field='place_offset',key='placement_residual_xy',kind='measured_place')
    for dx,dy in ((PROBE_STEP,0),(-PROBE_STEP,0),(0,PROBE_STEP),(0,-PROBE_STEP)):
        old = parameters.place_offset
        new = [round(old[0]+dx,PRECISION),round(old[1]+dy,PRECISION),old[2]]
        yield exploration(parameters,{'place_offset':new},'exploratory_place')


def grasp_options(parameters, evidence):
    yield measured(parameters,evidence,field='grasp_offset',key='grasp_residual_xy',kind='measured_grasp')
    count = evidence.get('diagnostics',{}).get('available_candidate_count')
    if type(count) is int:
        for index in range(min(count,5)):
            yield exploration(parameters,{'candidate_index':index},'exploratory_candidate')
    for delta in (-DEPTH_STEP,DEPTH_STEP):
        old = parameters.grasp_offset
        new = [old[0],old[1],round(old[2]+delta,PRECISION)]
        yield exploration(parameters,{'grasp_offset':new},'exploratory_depth')


def options(report, parameters):
    evidence = report.get('evidence',{})
    kind = report['error_type']
    diagnostics = evidence.get('diagnostics',{})
    phase = diagnostics.get('motion_segment') or diagnostics.get('failure_stage')
    if kind in PLACEMENT:
        yield from place_options(parameters,evidence)
        return
    if kind in ('empty_grasp','ik_failure','object_dropped','collision'):
        yield from grasp_options(parameters,evidence)
    if kind in ('object_dropped','object_toppled') or (kind=='collision' and phase in ('transport','lift')):
        yield exploration(parameters,{'time_scale':min(3.,parameters.time_scale*1.5)},'exploratory_slow')
    if kind=='collision' and phase in ('transport','lift'):
        yield exploration(parameters,{'lift_height':min(.48,max(.45,parameters.lift_height+.1))},'exploratory_lift')


def explain(row):
    field = next(iter(row['changes']))
    facts = row['facts']
    prefix = '实测补偿候选' if row['kind'].startswith('measured_') else '探索候选（作用尚未验证）'
    text = f"{prefix}：{field} 从 {facts['current_value']} 改为 {facts['new_value']}，单位 {facts['units']}。"
    if facts['measurement'] is not None:
        text += f"测量残差 {facts['measurement']}；实际变化 {facts['actual_delta']}；限幅轴 {facts['saturated']}。"
    return text


def candidates(report, values, history):
    parameters = Parameters().updated(values)
    rows, seen = [], set()
    tried = {digest(h.get('reflection',{}).get('changes',{})) for h in history}
    count = report.get('evidence',{}).get('diagnostics',{}).get('available_candidate_count')
    for row in options(report,parameters):
        if row is None:
            continue
        try:
            check_action(Reflection('',row['changes'],'rule_candidate'),parameters,candidate_count=count)
        except ValueError:
            continue
        key = digest(row['changes'])
        if key in seen or key in tried:
            continue
        seen.add(key)
        row.update(id='c_'+key[:12],source='rule_generated_candidate',explanation_source='deterministic_action_template')
        row['explanation'] = explain(row)
        rows.append(row)
    random.Random(int(digest([r['id'] for r in rows]),16)).shuffle(rows)
    return json.loads(json.dumps(rows))

"""限定既有参数自由度的固定动作诊断。"""
from reflection.reflector import Parameters
from recovery.references import scene_items,scene_build

LIFT_STANDARD = .45
LIFT_MAXIMUM = .48
XY_STEP = .03
Z_STEPS = (.03,.06)
CANDIDATES = (1,4)
SEED = 905001


def interventions():
    values = [('default',{}),('lift45',{'lift_height':LIFT_STANDARD}),
              ('lift48',{'lift_height':LIFT_MAXIMUM})]
    for axis,name in ((0,'x'),(1,'y')):
        for sign,label in ((-1,'minus'),(1,'plus')):
            offset = [0.,0.,0.]
            offset[axis] = sign*XY_STEP
            values.append((f'place_{name}_{label}',dict(lift_height=LIFT_STANDARD,place_offset=offset)))
    values.extend((f'place_z_{i}',dict(lift_height=LIFT_STANDARD,place_offset=[0,0,z])) for i,z in enumerate(Z_STEPS))
    values.extend((f'candidate_{i}',dict(lift_height=LIFT_STANDARD,candidate_index=i)) for i in CANDIDATES)
    return values


def items():
    selected = [r for r in scene_items() if r['source']=='PurpleCapsule' and r['seed']==SEED]
    return [dict(id=f"{s['id']}_{name}",scene_id=s['id'],variant=name,parameters=Parameters().updated(v).to_dict(),
                 **{k:x for k,x in s.items() if k!='id'}) for s in selected for name,v in interventions()]


def configuration(item):
    return scene_build(item['seed'],item['factor'])

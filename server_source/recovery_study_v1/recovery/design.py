"""预登记因素与预算，不按新恢复结果选择条件。"""
from copy import deepcopy
from controlled.config import tasks,scenario
from recovery.references import scene_build,scene_items

CASE = 47
MODES = ('noisy','ideal','missing_xy')
DIAGNOSTIC_ARMS = ('retry','priority','hybrid','candidate_depth','depth_candidate')
COLLISION_ARMS = ('retry','rule_stage','random','hybrid','guided')
TARGET_CANDIDATE = 1
TARGET_DEPTH = -.01
MAX_ATTEMPTS = 3
SELECTION_SEED = 906001


def runs():
    task = tasks()[CASE]
    rows = [dict(id=f'F_{mode}_{arm}',study='feedback',mode=mode,arm=arm,case=CASE,**task)
            for mode in MODES for arm in DIAGNOSTIC_ARMS]
    selected_seed = min(r['seed'] for r in scene_items())
    for item in scene_items():
        if item['seed']!=selected_seed:
            continue
        rows.extend(dict(id=f"{item['id']}_{arm}",scene_id=item['id'],study='collision',
                         arm=arm,fault='none',split='train',**{k:v for k,v in item.items() if k!='id'})
                    for arm in COLLISION_ARMS)
    return rows


def configuration(item):
    if item['study']=='collision':
        return scene_build(item['seed'],item['factor'])
    config = deepcopy(scenario(item['seed'],item['level']))
    if item['mode']!='noisy':
        config['feedback'] = dict(mode='ideal_measurement',residual_sigma_m=0,missing_probability=0)
    if item['mode']=='missing_xy':
        config['feedback'].update(mode='residuals_missing',hide_xy=True)
    return config


def sequence_changes(mode,parameters,*,step):
    if mode not in ('candidate_depth','depth_candidate') or step not in (0,1):
        raise ValueError('Unknown diagnostic sequence or step')
    candidate_turn = (mode=='candidate_depth') == (step==0)
    if candidate_turn:
        return {'candidate_index':TARGET_CANDIDATE}
    offset = list(parameters.grasp_offset)
    offset[2] = TARGET_DEPTH
    return {'grasp_offset':offset}


def smoke_ids():
    collision = next(r['id'] for r in runs() if r['study']=='collision' and r['arm']=='guided')
    return ('F_noisy_priority',collision)

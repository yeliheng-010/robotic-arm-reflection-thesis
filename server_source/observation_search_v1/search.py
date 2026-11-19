"""共享128全局观察，两个方法各自使用独立128后续预算。"""
import json
from camera_joint_v1.search import global_camera
from camera_joint_v1.candidates import local
from observation_search_v1 import candidates, record, pose
from observation_search_v1.common import METHODS, GLOBAL_BUDGET, ROUNDS, ROUND_BUDGET, save


def hydrated(entries, observations):
    return [dict(observations[e['uid']], **dict(e['candidate'], index=i)) for i, e in enumerate(entries)]


def append(env, resources, *, candidate, boxes, config, folder, state, owners):
    uid = len(state['observations'])
    if candidate['camera'] is None:
        row, data, rgb = dict(accepted=False, reason='no_candidate'), None, None
    else:
        row, data, rgb = record.capture(env, resources, camera=candidate['camera'], boxes=boxes,
            folder=folder, uid=uid, diagnostic=state['measured'] < 3)
    row.update(index=uid, camera=candidate['camera'])
    state['observations'].append(row)
    with (folder / 'observations.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    if data is not None:
        state['measured'] += 1
        if state['measured'] <= 3:
            state['diagnostic_indices'].append(uid)
    for method in owners:
        entry = dict(uid=uid, candidate=candidate)
        state['searches'][method].append(entry)
        if row['accepted'] and method not in state['accepted']:
            selected = dict(row, index=len(state['searches'][method])-1)
            state['accepted'][method] = pose.accepted(env, data, config=config, row=selected,
                                                      folder=folder / method, rgb=rgb)


def joint_pool(rows, config, boxes):
    if any('gate' in r for r in rows):
        return [dict(stage='joint', **r) for r in local(rows, boxes)]
    return [dict(stage='fallback', proposal_index=i, camera=global_camera(config, boxes, i))
            for i in range(GLOBAL_BUDGET, GLOBAL_BUDGET*2)]


def adaptive_pool(rows, config, *, boxes, round_index):
    result = [dict(stage='adaptive', **r) for r in candidates.batch(rows, boxes, round_index)]
    for slot in range(len(result), ROUND_BUDGET):
        index = GLOBAL_BUDGET + round_index*ROUND_BUDGET + slot
        result.append(dict(stage='adaptive_fallback', proposal_index=index, round=round_index,
                           camera=global_camera(config, boxes, index)))
    return result


def run(env, resources, *, config, boxes, folder):
    state = dict(observations=[], searches={m: [] for m in METHODS}, measured=0,
                 accepted={}, diagnostic_indices=[])
    def observe(candidate, owners):
        append(env, resources, candidate=candidate, owners=owners, config=config,
               boxes=boxes, folder=folder, state=state)
    for index in range(GLOBAL_BUDGET):
        observe(dict(stage='global', proposal_index=index, camera=global_camera(config, boxes, index)), METHODS)
    rows = hydrated(state['searches']['joint'], state['observations'])
    for candidate in joint_pool(rows, config, boxes):
        observe(candidate, ('joint',))
    for round_index in range(ROUNDS):
        rows = hydrated(state['searches']['adaptive'], state['observations'])
        for candidate in adaptive_pool(rows, config, boxes=boxes, round_index=round_index):
            observe(candidate, ('adaptive',))
    save(folder / 'observations.json', state.pop('observations'))
    save(folder / 'searches.json', state.pop('searches'))
    return state

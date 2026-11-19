"""同相机配对采集；旧采样观测决定固定局部池，不读取射线或拟合评价。"""
from sf_camera import framed
from sf_select import set_camera, verify_projection
from sd_render import depth_check
from camera_joint_v1.search import global_camera
from camera_joint_v1.candidates import local
import json
from sensor_independent_v1 import sensor, reference
from sensor_independent_v2 import pose, rgb_policy
from sensor_independent_v2.common import METHODS, GLOBAL_BUDGET, DIAGNOSTIC_VIEWS, save


def collect_one(env, resources, *, camera, boxes, folder, index):
    frame = framed(boxes, camera)
    if not frame['passed']:
        return dict(framing=frame, reason='framing_rejected'), None, None
    set_camera(env, camera)
    verify_projection(env, camera, boxes)
    before = sensor.rgb(env)
    data = {method: sensor.capture(env, resources[method], frame) for method in METHODS}
    rgb = sensor.rgb(env)
    rgb_check = rgb_policy.save_pair(before, rgb, folder=folder, index=index)
    for value in data.values():
        value['report'] = rgb_policy.qualify(value['report'], rgb_check)
    report = dict(framing=frame, methods={m: d['report'] for m, d in data.items()},
        fixed_old_mask=depth_check(env, data['no_msaa']['depth'], data['original']['roots']),
        rgb=rgb_check)
    return report, data, rgb


def process(env, resources, *, candidate, boxes, config, folder, state):
    row = dict(index=len(state['rows']), **candidate)
    if candidate['camera'] is None:
        state['rows'].append(row)
        journal(folder, row)
        return
    report, data, rgb = collect_one(env, resources, camera=candidate['camera'], boxes=boxes,
                                  folder=folder, index=row['index'])
    row.update(report)
    state['rows'].append(row)
    journal(folder, row)
    if data is None:
        return
    state['measured'] += 1
    if state['measured'] <= DIAGNOSTIC_VIEWS:
        reference.save_pair(env, data, folder=folder / f'pair_{row["index"]}', row=row, boxes=boxes)
        state['diagnostic_indices'].append(row['index'])
    for method, value in data.items():
        if method not in state['accepted'] and value['report']['accepted']:
            state['accepted'][method] = pose.accepted(env, value, config=config, row=row,
                                                      folder=folder / method, rgb=rgb)


def journal(folder, row):
    with (folder / 'observations.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')


def local_pool(state, config, boxes):
    original = [dict(index=r['index'], camera=r['camera'], **r['methods']['original'])
                for r in state['rows'] if 'methods' in r]
    if original:
        return (dict(stage='local', **row) for row in local(original, boxes))
    return (dict(stage='global_fallback', camera=global_camera(config, boxes, i), proposal_index=i)
            for i in range(GLOBAL_BUDGET, 2 * GLOBAL_BUDGET))


def run(env, resources, *, config, boxes, folder):
    state = dict(rows=[], measured=0, accepted={}, diagnostic_indices=[])
    for index in range(GLOBAL_BUDGET):
        candidate = dict(stage='global', proposal_index=index, camera=global_camera(config, boxes, index))
        process(env, resources, candidate=candidate, boxes=boxes, config=config, folder=folder, state=state)
    for candidate in local_pool(state, config, boxes):
        process(env, resources, candidate=candidate, boxes=boxes, config=config, folder=folder, state=state)
    save(folder / 'observations.json', state['rows'])
    return {key: value for key, value in state.items() if key != 'rows'}

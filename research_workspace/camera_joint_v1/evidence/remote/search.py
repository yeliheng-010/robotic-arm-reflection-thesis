"""同一静止场景、两个独立256候选预算，可复用完全相同的观测。"""
from copy import deepcopy
from time import perf_counter
from cv_select import evaluate
from sf_camera import framed, proposal
from camera_joint_v1.policy import BUDGET, GLOBAL_BUDGET
from camera_joint_v1.candidates import local


def observation(env, renderer, *, camera, boxes, cache):
    key = tuple([*camera['position'], *camera['target'], camera['fovy'],
                 *[v for row in camera.get('rotation', []) for v in row]])
    if key in cache:
        return deepcopy(cache[key]), True
    frame = framed(boxes, camera)
    report = (evaluate(env, renderer, camera, boxes=boxes) if frame['passed']
              else dict(accepted=False, framing=frame, reason='framing_rejected'))
    cache[key] = deepcopy(report)
    return report, False


def global_camera(config, boxes, index):
    return config['camera'] if index == 0 else proposal(config['seed'], index, boxes=boxes)


def append(rows, env, renderer, *, camera, boxes, cache, metadata):
    started = perf_counter()
    if camera is None:
        rows.append(dict(index=len(rows), camera=None, accepted=False, **metadata))
        return False
    report, reused = observation(env, renderer, camera=camera, boxes=boxes, cache=cache)
    rows.append(dict(index=len(rows), camera=camera, **report, **metadata,
                     cache_reused=reused, evaluation_seconds=perf_counter()-started))
    return report['accepted']


def run(env, renderer, *, config, boxes, method, cache):
    rows = []
    limit = BUDGET if method == 'original' else GLOBAL_BUDGET
    for index in range(limit):
        if append(rows, env, renderer, camera=global_camera(config, boxes, index),
                  boxes=boxes, cache=cache, metadata=dict(stage='global', proposal_index=index)):
            return rows
    if method == 'original':
        return rows
    if any('gate' in row for row in rows):
        candidates = local(rows, boxes)
    else:
        candidates = (dict(camera=global_camera(config, boxes, index), proposal_index=index)
                      for index in range(GLOBAL_BUDGET, BUDGET))
    for candidate in candidates:
        metadata = {k: v for k, v in candidate.items() if k not in ('camera', 'reason')}
        metadata['stage'] = 'local' if 'anchor_index' in candidate else 'global_fallback'
        if candidate['camera'] is None:
            metadata['reason'] = candidate['reason']
        accepted = append(rows, env, renderer, camera=candidate['camera'], boxes=boxes,
                          cache=cache, metadata=metadata)
        if accepted or len(rows) == BUDGET:
            break
    return rows

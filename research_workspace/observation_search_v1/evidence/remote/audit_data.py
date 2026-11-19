import json
import numpy as np
from cv_policy import frame_gate
from sf_camera import framed
from sensor_independent_v2.rgb_policy import assess, qualify
from observation_search_v1 import stable, search
from observation_search_v1.common import read, METHODS, GLOBAL_BUDGET, ROUNDS, ROUND_BUDGET
from camera_joint_v1.search import global_camera


def check_rgb(folder, row):
    with np.load(folder / f'rgb_{row["index"]}.npz') as packed:
        frames = stable.decode(packed)
    rgb = row['rgb']
    assert len(frames) == rgb['stability']['count']+1
    stable.check_record(frames[:-1], rgb['stability'])
    assert assess(frames[-2], frames[-1]) == rgb['post']
    assert assess(frames[0], frames[-1]) == rgb['initial']
    assert rgb['eligible'] == (rgb['stability']['passed'] and rgb['post']['passed'])


def check_observations(folder, boxes):
    observations = read(folder / 'observations.json')
    journal = [json.loads(s) for s in (folder / 'observations.jsonl').read_text(encoding='utf-8').splitlines()]
    assert observations == journal
    for uid, row in enumerate(observations):
        assert row['index'] == uid
        if row['camera'] is not None:
            assert framed(boxes, row['camera']) == row['framing']
        if 'rgb' in row:
            check_rgb(folder, row)
            assert frame_gate(row['measurements']) == row['gate']
            assert qualify(row, dict(passed=row['rgb']['eligible'])) == row
        else:
            assert not row['accepted']
    return observations


def check_searches(folder, observations, *, config, boxes):
    searches = read(folder / 'searches.json')
    expected_global = [dict(stage='global', proposal_index=i, camera=global_camera(config, boxes, i))
                       for i in range(GLOBAL_BUDGET)]
    assert searches['joint'][:GLOBAL_BUDGET] == searches['adaptive'][:GLOBAL_BUDGET]
    for method in METHODS:
        entries = searches[method]
        assert GLOBAL_BUDGET <= len(entries) <= 256
        assert [e['candidate'] for e in entries[:GLOBAL_BUDGET]] == expected_global
        for entry in entries:
            assert entry['candidate']['camera'] == observations[entry['uid']]['camera']
    rows = search.hydrated(searches['joint'][:GLOBAL_BUDGET], observations)
    assert [e['candidate'] for e in searches['joint'][GLOBAL_BUDGET:]] == search.joint_pool(rows, config, boxes)
    for number in range(ROUNDS):
        offset = GLOBAL_BUDGET+number*ROUND_BUDGET
        rows = search.hydrated(searches['adaptive'][:offset], observations)
        expected = search.adaptive_pool(rows, config, boxes=boxes, round_index=number)
        assert [e['candidate'] for e in searches['adaptive'][offset:offset+ROUND_BUDGET]] == expected
    expected_uids = list(range(len(observations)))
    actual_uids = [e['uid'] for e in searches['joint']] + [e['uid'] for e in searches['adaptive'][GLOBAL_BUDGET:]]
    assert actual_uids == expected_uids
    return searches


def rgb_statistics(observations):
    rows = [r['rgb'] for r in observations if 'rgb' in r]
    return dict(measured=len(rows), first_to_final_failures=sum(not r['initial']['passed'] for r in rows),
        first_adjacent_failures=sum(not r['stability']['checks'][0]['passed'] for r in rows),
        stability_failures=sum(not r['stability']['passed'] for r in rows),
        post_failures=sum(not r['post']['passed'] for r in rows),
        recovered=sum(not r['initial']['passed'] and r['eligible'] for r in rows),
        frames=sum(r['stability']['count'] for r in rows))

"""拟合和选择阶段不接受真值参数。"""
from visibility_calibration_v1 import fitting as original
from visibility_calibration_v1.analysis import single_quality
from pose_replay_v1 import runtime as repaired
from pose_selective_v1.policy import choose
from pose_fresh_v1.policy import pairs, REPEATS


def single(cloud):
    value = original.single(cloud)
    value['quality_passed'] = bool(single_quality(value['fit']))
    return dict(original=value, repaired=repaired.single(cloud))


def pair(clouds, singles):
    old = original.pair(*clouds, fits=[s['original'] for s in singles])
    new = repaired.pair(clouds, [s['repaired'] for s in singles])
    return dict(original=old, repaired=new)


def selected(value):
    return dict(value, choice=choose(value['original']['quality_passed'],
                                    value['repaired']['quality_passed']))


def run(rows, clouds):
    singles, cache = [], {}
    for index in sorted(clouds):
        for repeat, cloud in enumerate(clouds[index]):
            value = selected(single(cloud))
            cache[index, repeat] = value
            singles.append(dict(index=index, repeat=repeat, **value))
    combined = []
    chosen = pairs(rows)
    for a, b in chosen:
        for repeat in range(REPEATS):
            value = pair([clouds[a][repeat], clouds[b][repeat]],
                         [cache[a, repeat], cache[b, repeat]])
            combined.append(dict(indices=[a, b], repeat=repeat, **selected(value)))
    return dict(singles=singles, pairs=combined, selected_pairs=chosen)

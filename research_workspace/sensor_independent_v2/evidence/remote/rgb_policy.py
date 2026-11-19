"""复用既有RGB容差；逐位相等与容差通过分别记录。"""
import hashlib
import numpy as np
from cv_rgb import compare


def assess(before, after):
    return dict(compare(before, after), bitwise_equal=bool(np.array_equal(before, after)),
        before_sha256=hashlib.sha256(before.tobytes()).hexdigest(),
        after_sha256=hashlib.sha256(after.tobytes()).hexdigest(), shape=list(before.shape))


def qualify(report, rgb):
    geometry = bool(report['gate']['passed'] and report['calibration']['passed'])
    return dict(report, geometry_accepted=geometry, accepted=bool(geometry and rgb['passed']))


def save_pair(before, after, *, folder, index):
    path = folder / f'rgb_{index}.npz'
    with path.open('xb') as stream:
        np.savez_compressed(stream, before=before, after=after)
    return assess(before, after)

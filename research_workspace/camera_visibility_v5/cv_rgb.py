"""仅容许稀疏的RGB量化差；可见性、深度与几何门槛不变。"""
import cv2
import numpy as np

MAX_CHANNEL_DELTA = 2
MAX_CHANGED_FRACTION = .001


def compare(expected, actual):
    if expected.shape != actual.shape:
        return dict(passed=False, reason='shape_mismatch')
    delta = np.abs(expected.astype(int)-actual.astype(int))
    changed = np.any(delta != 0, axis=-1)
    maximum, fraction = int(delta.max()), float(changed.mean())
    return dict(passed=maximum <= MAX_CHANNEL_DELTA and fraction <= MAX_CHANGED_FRACTION,
                max_channel_delta=maximum, changed_fraction=fraction,
                changed_pixels=int(changed.sum()))


def compare_files(expected, actual):
    one, two = cv2.imread(str(expected)), cv2.imread(str(actual))
    if one is None or two is None:
        raise ValueError('Missing RGB image')
    result = compare(one, two)
    if not result['passed']:
        raise ValueError('RGB reconstruction differs: '+str(result))
    return result

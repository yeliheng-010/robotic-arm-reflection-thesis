"""只依据当前观测质量排序，不接收任务成败或位姿真值。"""
import math
SEEDS = tuple(range(978201, 978213))
BUDGET = 256
GLOBAL_BUDGET = 128
ANCHORS = 4
NOISE_PREFIX = 978601
SLENDER = ('Hammer', 'Knife', 'Flashlight')
FOVY_BOUNDS = (48., 65.)
IMAGE_CENTER = 320.
SNUG_LOW, SNUG_HIGH = 25., 614.


def score(row):
    deficits = []
    for name, values in row['measurements'].items():
        gate = row['gate']['objects'][name]
        slender = name in SLENDER
        ratios = [values['pixels'] / (256 if slender else 576),
                  values['short_side'] / (12 if slender else 16),
                  gate.get('visible_fraction', 0.) / .85, gate.get('component_fraction', 0.) / .8]
        if slender:
            ratios.append(values['long_side'] / 24)
        deficits.extend(max(0., 1. - value) for value in ratios)
    return (len(row['gate']['rejected']), max(deficits), sum(deficits), row['index'])


def fovy_for_pixels(camera, pixels):
    flat = [float(value) for point in pixels for value in point]
    if not flat or not all(math.isfinite(value) for value in flat):
        return None
    ratio = max((max(flat) - IMAGE_CENTER) / (SNUG_HIGH - IMAGE_CENTER),
                (IMAGE_CENTER - min(flat)) / (IMAGE_CENTER - SNUG_LOW))
    required = math.degrees(2 * math.atan(math.tan(math.radians(camera['fovy'] / 2)) * ratio))
    return max(FOVY_BOUNDS[0], required) if required <= FOVY_BOUNDS[1] else None

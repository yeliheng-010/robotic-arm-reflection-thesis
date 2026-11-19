"""最多4帧、连续2次满足原RGB容差；无物理积分、无无限重试。"""
import numpy as np
from sensor_independent_v2.rgb_policy import assess

MAX_FRAMES = 4
REQUIRED_PASSES = 2


def settle(render):
    frames, checks, streak = [render()], [], 0
    while len(frames) < MAX_FRAMES:
        frames.append(render())
        check = assess(frames[-2], frames[-1])
        checks.append(check)
        streak = streak + 1 if check['passed'] else 0
        if streak >= REQUIRED_PASSES:
            break
    return frames, dict(passed=streak >= REQUIRED_PASSES, checks=checks, count=len(frames))


def encode(frames):
    values = np.stack(frames).astype(np.int16)
    return dict(first=frames[0], deltas=np.diff(values, axis=0).astype(np.int16))


def decode(data):
    first = np.asarray(data['first'], dtype=np.int32)
    rest = first + np.cumsum(data['deltas'], axis=0, dtype=np.int32)
    values = np.concatenate([first[None], rest], axis=0)
    assert np.all((values >= 0) & (values <= 255))
    return [v.astype(np.uint8) for v in values]


def check_record(frames, report):
    frames = iter(frames)
    actual, checked = settle(lambda: next(frames))
    assert checked == report
    return actual[-1]

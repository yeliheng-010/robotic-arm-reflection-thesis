import numpy as np
from sf_camera import framed
from sf_select import set_camera, verify_projection
from sd_render import depth_check
from sensor_independent_v1 import sensor, reference
from sensor_independent_v2.rgb_policy import assess, qualify
from observation_search_v1 import stable


def capture(env, resources, *, camera, boxes, folder, uid, diagnostic):
    frame = framed(boxes, camera)
    if not frame['passed']:
        return dict(framing=frame, accepted=False, reason='framing_rejected'), None, None
    set_camera(env, camera)
    verify_projection(env, camera, boxes)
    frames, stability = stable.settle(lambda: sensor.rgb(env))
    data = dict(no_msaa=sensor.capture(env, resources['no_msaa'], frame))
    if diagnostic:
        data['original'] = sensor.capture(env, resources['original'], frame)
    after = sensor.rgb(env)
    rgb = dict(stability=stability, post=assess(frames[-1], after), initial=assess(frames[0], after))
    rgb['eligible'] = bool(stability['passed'] and rgb['post']['passed'])
    with (folder / f'rgb_{uid}.npz').open('xb') as stream:
        np.savez_compressed(stream, **stable.encode(frames+[after]))
    for values in data.values():
        values['report'] = qualify(values['report'], dict(passed=rgb['eligible']))
    row = dict(data['no_msaa']['report'], rgb=rgb, index=uid, camera=camera)
    if diagnostic:
        paired_row = dict(row, methods={m: d['report'] for m, d in data.items()},
            fixed_old_mask=depth_check(env, data['no_msaa']['depth'], data['original']['roots']))
        reference.save_pair(env, data, folder=folder / f'pair_{uid}', row=paired_row, boxes=boxes)
    return row, data['no_msaa'], after

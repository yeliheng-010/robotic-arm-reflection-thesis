import numpy as np
from diversity.noise import corrupt_depth
from span import world_points

NAMESPACE = 965901


def projection(position, calibration, *, shape, roots, body_id):
    matrix = np.asarray(calibration['camera_transform'])
    point = matrix[:3,:3].T@(np.asarray(position)-matrix[:3,3])
    fx, fy, cx, cy = calibration['intrinsics']
    if point[2] <= 0:
        return dict(passed=False, status='behind_camera', pixel=None)
    u, v = int(round(fx*point[0]/point[2]+cx)), int(round(fy*point[1]/point[2]+cy))
    inside = 0 <= v < shape[0] and 0 <= u < shape[1]
    matched = bool(inside and roots[v,u] == body_id)
    return dict(passed=matched, status='matched' if matched else 'other_root' if inside else 'outside_image', pixel=[u,v])


def derive(folder, config, *, item, calibration):
    with np.load(folder/'sensor.npz') as arrays:
        depth, roots = arrays['depth'], arrays['roots']
        projected = {role: projection(calibration['body_positions'][item[role]], calibration, shape=depth.shape,
            roots=roots, body_id=calibration['body_ids'][item[role]]) for role in ('source','destination')}
        seed = [NAMESPACE, config['seed']]
        noisy, stats = corrupt_depth(depth, config['sensor'], seed=np.random.SeedSequence(seed))
        mask = (roots == calibration['body_ids'][item['source']]) & (noisy > .05) & (noisy < 2.)
        points = world_points(noisy, mask, dict(transform=calibration['camera_transform'], intrinsics=calibration['intrinsics']))
    return projected, points, dict(seed=seed, stats=stats, purpose='qualification_noise_not_execution_identity')

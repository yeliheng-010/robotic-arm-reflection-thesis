import os
from pathlib import Path
import cv2
import numpy as np
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCES = ('natural_observable_preflight_v1', 'safe_visual_preflight_v1')


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


def inspect(source, case):
    key = str(case['item']['seed'])+'_'+case['item']['group']
    folder = source/'renders'/key
    if case['item']['group'] == 'baseline' and source.name == 'safe_visual_preflight_v1':
        folder = ROOT.parent/'natural_observable_preflight_v1/renders/962801_baseline'
    calibration = read(folder/'result.json')
    assert sha(folder/'sensor.npz') == calibration['sensor_sha256']
    assert sha(folder/'rgb.png') == calibration['rgb_sha256']
    shape = cv2.imread(str(folder/'rgb.png')).shape
    rows = {}
    with np.load(folder/'sensor.npz') as data:
        for role in ('source', 'destination'):
            name = case['item'][role]
            rows[role] = projection(calibration['body_positions'][name], calibration,
                shape=shape, roots=data['roots'], body_id=calibration['body_ids'][name])
    return dict(id=case['item']['id'], passed=all(r['passed'] for r in rows.values()), roles=rows,
        render=str(folder), calibration_sha256=sha(folder/'result.json'))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    results = {}
    for name in SOURCES:
        source = ROOT.parent/name
        manifest, result = read(source/'manifest.json'), read(source/'result.json')
        assert all(sha(p) == h for p,h in manifest['identities'].items())
        passed = {r['id'] for r in result['rows'] if r['passed']}
        rows = [inspect(source, case) for case in manifest['cases'] if case['item']['id'] in passed]
        results[name] = dict(rows=rows, admitted=sum(r['passed'] for r in rows),
            source_manifest_sha256=sha(source/'manifest.json'), source_result_sha256=sha(source/'result.json'))
        print(name, results[name]['admitted'], len(rows), flush=True)
    save(ROOT/'result.json', dict(sources=results, physical_attempts=0, model_calls=0,
        limitation='Current simulated body-centre grounding qualification, not an RGB detector or global visibility guarantee',
        identities={str(Path(__file__)):sha(Path(__file__))}))


if __name__ == '__main__':
    main()

"""重新检查新视角的真实图像与原噪声点云/规划资格。"""
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene, evaluate
from cv_policy import REQUIRED
from sd_inventory import root_boxes
from sd_render import capture
from qualification_data import derive
from qual_one_v2 import reference
import span_qualify
from cc_common import PILOT, current, read, save, sha

MIN_POINTS = 64


def render(case, folder):
    folder.mkdir(parents=True, exist_ok=False)
    with scene(case['config']) as (env, renderer):
        boxes = root_boxes(env.mj_model, env.mj_data)
        gate = evaluate(env, renderer, case['config']['camera'], boxes={n: boxes[n] for n in REQUIRED})
        save(folder/'visibility.json', gate)
        if not gate['accepted']:
            return None
        report = capture(env, folder)
        save(folder/'result.json', report)
        return report


def qualify(case):
    seed = case['item']['seed']
    folder = PILOT/'qualification'/str(seed)
    report = render(case, folder/'render')
    row = dict(seed=seed, qualified=False, status='live_visibility_rejected')
    if report is not None:
        assert report['calibration']['passed']
        projected, points, noise = derive(folder/'render', case['config'],
            item=case['item'], calibration=report)
        row.update(projection=projected, qualification_noise=noise, points=len(points))
        row['status'] = 'grounding_projection_rejected'
        if all(r['passed'] for r in projected.values()):
            row['status'] = 'insufficient_noisy_target_points'
            if len(points) >= MIN_POINTS:
                with patch.object(span_qualify, 'ROOT', folder):
                    row['geometry'] = span_qualify.qualify(case, reference(), points)
                row.update(qualified=row['geometry']['passed'], status=row['geometry']['status'])
    row['manifest_sha256'] = sha(PILOT/'manifest.json')
    save(folder/'result.json', row)
    print(row, flush=True)


if __name__ == '__main__':
    qualify(current(int(sys.argv[1])))

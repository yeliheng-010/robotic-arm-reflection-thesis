import os
import unittest
from pathlib import Path
import cv2
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from cm_pose import poses
from geometry.candidates import MAX_WIDTH
from f_common import read, save, sha
from span import span, world_points

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_deeper_pilot_v1'
CASES = (('D1_962801_baseline', 1), ('D0_962802_varied_noisy', 3),
         ('D1_962802_varied_noisy', 3), ('D0_962803_varied_noisy', 1))


def examine(name, index):
    audit = read(SOURCE/'audits'/(name+'.json'))
    assert audit['passed'] and audit['manifest_sha256'] == sha(SOURCE/'manifest.json')
    folder = SOURCE/'cases'/name/f'attempt_{index}'
    record = read(folder/'execution/result.json')['records'][0]
    depth_path, field = folder/'execution/attempt_1/depth_evidence.npz', 'noisy'
    if record['depth_recovery']['changed']:
        depth_path, field = Path(record['depth_recovery']['artifact']), 'effective'
    mask_path = folder/'execution/attempt_1/mask.png'
    paths = [depth_path, mask_path, folder/'route.json', folder/'observation_summary.json']
    assert all(sha(p) == audit['identities'][str(p)] for p in paths)
    with np.load(depth_path) as data:
        depth = data[field]
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE) > 0
    calibration = read(folder/'observation_summary.json')['private'][0]
    points = world_points(depth, mask, calibration)
    plan = read(folder/'route.json')
    nominal = sm.SE3(np.array(plan['context']['nominal']))
    selected = plan['selected']
    rows = [dict(id=p['id'], span_m=span(points, p['pose'].R[:,1])) for p in poses(nominal)]
    selected_span = span(points, np.array(selected['pose'])[:3,1])
    return dict(condition=name, attempt=index, success=read(folder/'step.json')['success'],
        points=len(points), original_grasp_generator_max_width_m=MAX_WIDTH,
        selected=selected['id'], selected_observed_span_m=selected_span,
        poses=rows, source='saved_simulation_assisted_mask_and_noisy_depth_not_object_true_dimensions',
        identities={str(p):sha(p) for p in paths})


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    rows = [examine(name, index) for name,index in CASES]
    save(ROOT/'result.json', dict(rows=rows, tests=tested.testsRun, physical_attempts=0, model_calls=0,
        limitation='Observed surface percentile span; incomplete surface is not complete object width or proof of grasp success',
        identities={str(p):sha(p) for p in ROOT.glob('*.py')}))
    for row in rows:
        print({k:v for k,v in row.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()

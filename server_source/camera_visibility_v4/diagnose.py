import os
from pathlib import Path
import cv2
import numpy as np
from sd_common import read, save
from sd_inventory import root_boxes
from cv_select import scene, evaluate, image
from cv_policy import REQUIRED

ROOT = Path(__file__).resolve().parent


def main():
    job = os.environ['SLURM_JOB_ID']
    source = ROOT.parent/'camera_visibility_v2/runs/job_6300/964103'
    old = read(source/'selection.json')['attempts'][0]
    cases = read(ROOT.parent/'recovery_collection_v1/batches/003/physics/manifest.json')['cases']
    config = next(c['config'] for c in cases if c['item']['id'] == 'R0_964103_varied_noisy')
    output = ROOT/'diagnosis'/('job_'+job)
    output.mkdir(parents=True, exist_ok=False)
    with scene(config) as (env, renderer):
        boxes = root_boxes(env.mj_model, env.mj_data)
        actual = evaluate(env, renderer, config['camera'], boxes={n: boxes[n] for n in REQUIRED})
        image(env, output/'after_evaluate.png')
    a = cv2.imread(str(source/'before.png')).astype(int)
    b = cv2.imread(str(ROOT/'runs/job_6302/964103/before.png')).astype(int)
    c = cv2.imread(str(output/'after_evaluate.png')).astype(int)
    value = dict(before_evaluate_max_diff=int(abs(a-b).max()),
        before_evaluate_changed_pixels=int(np.any(a != b, axis=2).sum()),
        after_evaluate_max_diff=int(abs(a-c).max()),
        after_evaluate_changed_pixels=int(np.any(a != c, axis=2).sum()),
        metrics_identical=actual['measurements'] == old['measurements'],
        old_gate=old['gate'], new_gate=actual['gate'])
    save(output/'result.json', value)
    print(value, flush=True)


if __name__ == '__main__':
    main()

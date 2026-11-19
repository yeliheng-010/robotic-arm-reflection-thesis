from pathlib import Path
import cv2
import numpy as np
from qualified_model_v1.common import ROOT, PROJECT, RUN, read, save, sha, verify
from qualified_model_v1.segmentation import select, world_points, MIN_POINTS
from qualified_model_v1.policy import pixel

WEIGHT = Path('/home/yeliheng/VLM_Grasp_Interactive/sam_b.pt')


def predict(predictor, entry):
    seed = entry['seed']
    folder = RUN/f'sam/{seed}'
    folder.mkdir(parents=True, exist_ok=False)
    prediction = read(RUN/f'{seed}/validated.json')
    if not prediction['valid'] or prediction['parsed']['action'] != 'LOCATE':
        save(folder/'result.json', dict(accepted=False, reason='no_model_location', sam_calls=0))
        return
    source = PROJECT/f'qualified_task_v1/run/audit/{seed}'
    with np.load(source/'public_sensor.npz') as sensor:
        image, depth = sensor['img'].copy(), sensor['depth'].copy()
    point = pixel(prediction['parsed']['source_pixel'], width=image.shape[1], height=image.shape[0])
    save(folder/'call_started.json', dict(point=point, sensor_sha256=sha(source/'public_sensor.npz')))
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    results = predictor(bgr, points=[point], labels=[1])
    mask, result = select(results, shape=depth.shape, point=point)
    if mask is not None:
        calibration = read(PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/calibration.json')
        points = world_points(depth, mask, calibration=calibration)
        with (folder/'prediction.npz').open('xb') as stream:
            np.savez_compressed(stream, mask=mask, world_points=points)
        from observed_top_pose_v1.top_fit import estimate
        result.update(valid_depth_points=len(points), top_estimate=estimate(points),
                      accepted=len(points) >= MIN_POINTS)
        overlay = bgr.copy()
        overlay[mask] = (.5*overlay[mask]+.5*np.array([0, 255, 0])).astype(np.uint8)
        cv2.drawMarker(overlay, tuple(point), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        assert cv2.imwrite(str(folder/'mask_overlay.png'), overlay)
    save(folder/'result.json', dict(result, sam_calls=1, physical_attempts=0, training_runs=0,
        source='RGB plus model point; noisy depth; no simulator mask or center'))
    print(dict(seed=seed, **result), flush=True)


def main():
    manifest = verify()
    assert WEIGHT.is_file()
    paths = [ROOT/n for n in ('sam.py', 'segmentation.py', 'test_segmentation.py', 'sam.sbatch')]
    paths += [WEIGHT]
    for entry in manifest['entries']:
        seed = entry['seed']
        paths.extend([RUN/f'{seed}/validated.json',
            PROJECT/f'qualified_task_v1/run/audit/{seed}/public_sensor.npz',
            PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/calibration.json'])
    save(RUN/'sam_manifest.json', dict(identities={str(p): sha(p) for p in paths},
        max_sam_calls=2, max_task_attempts=0, max_training_runs=0, simulated_mask_input=False))
    from ultralytics.models.sam import Predictor
    predictor = Predictor(overrides=dict(task='segment', mode='predict', model=str(WEIGHT),
                                          conf=.25, save=False, device=0))
    for entry in manifest['entries']:
        predict(predictor, entry)
    assert all(sha(p) == h for p, h in read(RUN/'sam_manifest.json')['identities'].items())


if __name__ == '__main__':
    main()

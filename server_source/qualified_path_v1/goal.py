"""以模型容器点提示SAM，保存原始预测后构建观测目标。"""
import cv2
import numpy as np
from qualified_model_v1.segmentation import select, world_points
from qualified_model_v1.policy import pixel
from qualified_path_v1.common import ROOT, PROJECT, RUN, SEEDS, read, save, sha, verify
from qualified_path_v1.observed import build

WEIGHT = PROJECT.parent/'VLM_Grasp_Interactive/sam_b.pt'
PIXEL_RADIUS = 2


def anchor(depth, mask, *, point, calibration):
    u, v = point
    nearby = np.zeros_like(mask)
    nearby[max(0, v-PIXEL_RADIUS):v+PIXEL_RADIUS+1, max(0, u-PIXEL_RADIUS):u+PIXEL_RADIUS+1] = True
    cloud = world_points(depth, mask & nearby, calibration=calibration)
    if len(cloud) < 3:
        raise ValueError('model_destination_depth_unavailable')
    return np.median(cloud, axis=0)


def capture(predictor, seed):
    folder = RUN/f'goals/{seed}'
    folder.mkdir(parents=True, exist_ok=False)
    source = PROJECT/f'qualified_task_v1/run/audit/{seed}'
    with np.load(source/'public_sensor.npz') as values:
        image, depth = values['img'], values['depth']
    predicted = read(PROJECT/f'qualified_model_v1/run/{seed}/validated.json')['parsed']['destination_pixel']
    point = pixel(predicted, width=image.shape[1], height=image.shape[0])
    save(folder/'call_started.json', dict(point=point, sensor_sha256=sha(source/'public_sensor.npz')))
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    results = predictor(bgr, points=[point], labels=[1])
    mask, score = select(results, shape=depth.shape, point=point)
    if mask is None:
        save(folder/'result.json', score)
        return
    calibration = read(PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/calibration.json')
    # 仅做原3x3像素侵蚀去掉预测轮廓边界，不使用私有分割。
    interior = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    cloud = world_points(depth, interior, calibration=calibration)
    with np.load(PROJECT/f'qualified_model_v1/run/sam/{seed}/prediction.npz') as values:
        source_cloud = values['world_points']
    with (folder/'prediction.npz').open('xb') as stream:
        np.savez_compressed(stream, mask=mask, interior=interior, world_points=cloud)
    try:
        geometry = build(source_cloud, cloud, anchor=anchor(depth, interior, point=point, calibration=calibration))
        save(folder/'geometry.json', geometry)
        result = dict(accepted=True, centers=len(geometry['centers']))
    except ValueError as error:
        result = dict(accepted=False, reason=str(error))
    save(folder/'result.json', dict(result, sam=score, physical_attempts=0, training_runs=0))
    print(dict(seed=seed, **result), flush=True)


def main():
    verify()
    from ultralytics.models.sam import Predictor
    predictor = Predictor(overrides=dict(task='segment', mode='predict', model=str(WEIGHT),
                                         conf=.25, save=False, device=0))
    for seed in SEEDS:
        capture(predictor, seed)
    verify()


if __name__ == '__main__':
    main()

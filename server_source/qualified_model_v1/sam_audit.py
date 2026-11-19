"""保存预测后独立评分；真值不参与SAM掩码选择或点云构建。"""
import numpy as np
from qualified_model_v1.common import ROOT, PROJECT, RUN, read, save, sha, verify
from qualified_model_v1.segmentation import world_points


def evaluate(entry):
    seed = entry['seed']
    folder, source = RUN/f'sam/{seed}', PROJECT/f'qualified_task_v1/run/audit/{seed}'
    result = read(folder/'result.json')
    if not result['accepted']:
        return dict(seed=seed, accepted=False, reason=result.get('reason'))
    with np.load(folder/'prediction.npz') as data:
        mask, points = data['mask'], data['world_points']
    with np.load(source/'private_roots.npz') as data:
        identity = read(source/'result.json')['replay']['body_ids']['PurpleCapsule']
        truth = data['roots'] == identity
    intersection = int(np.count_nonzero(mask & truth))
    with np.load(source/'public_sensor.npz') as sensor:
        calibration = read(PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/calibration.json')
        np.testing.assert_array_equal(points, world_points(sensor['depth'], mask, calibration=calibration))
    return dict(seed=seed, accepted=True, iou=intersection/int(np.count_nonzero(mask | truth)),
        precision=intersection/int(mask.sum()), recall=intersection/int(truth.sum()),
        valid_depth_points=len(points), top_estimate_available=result['top_estimate']['available'],
        predicted_mask_sha256=sha(folder/'prediction.npz'), independent_projection_verified=True)


def main():
    manifest = verify()
    sources = read(RUN/'sam_manifest.json')['identities']
    assert all(sha(p) == h for p, h in sources.items())
    rows = [evaluate(entry) for entry in manifest['entries']]
    result = dict(rows=rows, sam_calls=2, physical_attempts=0, training_runs=0,
                  audit_sha256=sha(ROOT/'sam_audit.py'), private_evaluation_only=True)
    save(RUN/'sam_audit_result.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()

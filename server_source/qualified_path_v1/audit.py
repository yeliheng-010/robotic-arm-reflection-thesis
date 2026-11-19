"""重建观测目标与完整规划；预测冻结之后才读取私有评分图。"""
import cv2
import numpy as np
from qualified_path_v1.worker import inspect, approved
from qualified_path_v1.common import ROOT, PROJECT, RUN, SEEDS, read, save, sha, verify
from qualified_path_v1.goal import anchor
from qualified_path_v1.observed import build
from qualified_model_v1.segmentation import world_points


def goal(seed, case):
    folder = RUN/f'goals/{seed}'
    source = PROJECT/f'qualified_task_v1/run/audit/{seed}'
    with np.load(source/'public_sensor.npz') as values:
        depth = values['depth']
    with np.load(folder/'prediction.npz') as values:
        mask, interior, points = (values[n] for n in ('mask', 'interior', 'world_points'))
    np.testing.assert_array_equal(interior, cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool))
    calibration = read(PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/calibration.json')
    rebuilt = world_points(depth, interior, calibration=calibration)
    np.testing.assert_array_equal(points, rebuilt)
    point = read(folder/'call_started.json')['point']
    with np.load(PROJECT/f'qualified_model_v1/run/sam/{seed}/prediction.npz') as values:
        source_points = values['world_points']
    geometry = build(source_points, rebuilt, anchor=anchor(depth, interior, point=point, calibration=calibration))
    assert geometry == read(folder/'geometry.json')
    identity = read(source/'result.json')['replay']['body_ids'][case['item']['destination']]
    with np.load(source/'private_roots.npz') as values:
        truth = values['roots'] == identity
    intersection = int(np.count_nonzero(mask & truth))
    return dict(seed=seed, geometry_identical=True, centers=len(geometry['centers']),
        iou=intersection/int(np.count_nonzero(mask | truth)),
        precision=intersection/int(mask.sum()), recall=intersection/int(truth.sum()))


def path(seed, case):
    folder = approved(seed)
    if folder is None:
        return dict(seed=seed, skipped=True, reason='grasp_endpoint_rejected')
    recorded = read(RUN/f'planning/{seed}/private_result.json')
    rebuilt = inspect(case, read(folder/'proposal.json'), geometry=read(RUN/f'goals/{seed}/geometry.json'))
    assert recorded == rebuilt
    return dict(seed=seed, independent_rebuild_identical=True, status=rebuilt['plan']['status'],
        passed=rebuilt['strict']['passed'], state_check=rebuilt['state_check'])


def main():
    verify()
    frozen = {str(p): sha(p) for p in RUN.rglob('*') if p.is_file()}
    planning = read(RUN/'planning_manifest.json')['identities']
    assert all(sha(p) == h for p, h in planning.items())
    cases = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases']
    goals = [goal(seed, cases[str(seed)]) for seed in SEEDS]
    paths = [path(seed, cases[str(seed)]) for seed in SEEDS]
    verify()
    assert all(sha(p) == h for p, h in frozen.items())
    result = dict(passed=True, goals=goals, paths=paths, identities=frozen,
        audit_sha256=sha(ROOT/'audit.py'), physical_attempts=0, model_calls=0,
        sam_calls=0, training_runs=0, independent_process=True)
    save(RUN/'audit_result.json', result)
    print(dict(passed=True, goals=goals, paths=paths), flush=True)


if __name__ == '__main__':
    main()

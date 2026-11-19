import numpy as np
from qualified_model_v1.segmentation import world_points
from model_grasp_intent_v1.requests import build, messages
from qualified_intent_v1.common import ROOT, PROJECT, RUN, SEEDS, read, save, sha


def observation(seed):
    source = PROJECT/f'qualified_model_v1/run/sam/{seed}'
    result = read(source/'result.json')
    assert result['accepted'] and result['top_estimate']['available']
    with np.load(source/'prediction.npz') as data:
        mask, target = data['mask'], data['world_points']
    frame = PROJECT/f'qualified_task_v1/run/audit/{seed}'
    calibration = read(PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/calibration.json')
    with np.load(frame/'public_sensor.npz') as data:
        scene = world_points(data['depth'], ~mask, calibration=calibration)
    scene = scene[np.linalg.norm(scene-np.median(target, axis=0), axis=1) <= .30]
    raw = dict(qualified=True, revision=0, target_points=target.tolist(),
               scene_points=scene.tolist(), nominal=result['top_estimate']['center'])
    request = build(raw, dict(decisions=1, planning=1, observations=0), history=[], can_observe=False)
    folder = RUN/str(seed)
    save(folder/'observation.json', raw)
    save(folder/'request.json', dict(seed=seed, image=str(frame/'qualified.png'), messages=messages(request)))
    return dict(seed=seed, request=str(folder/'request.json'), image_sha256=sha(frame/'qualified.png'))


def main():
    entries = [observation(seed) for seed in SEEDS]
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')]
    paths.extend(p for p in RUN.rglob('*.json'))
    for seed in SEEDS:
        paths.extend([PROJECT/f'qualified_model_v1/run/sam/{seed}/prediction.npz',
            PROJECT/f'qualified_task_v1/run/audit/{seed}/public_sensor.npz',
            PROJECT/f'qualified_task_v1/run/audit/{seed}/qualified.png'])
    save(RUN/'manifest.json', dict(entries=entries, identities={str(p): sha(p) for p in paths},
        max_model_calls=2, max_endpoint_evaluations_per_layout=8, max_task_attempts=0,
        max_training_runs=0, source='Predicted SAM mask; measured noisy depth; observed top nominal',
        private_truth_to_model=False, scope='model_intent_and_grasp_endpoint_preflight'))
    print(dict(registered=2), flush=True)


if __name__ == '__main__':
    main()

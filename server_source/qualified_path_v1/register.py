from qualified_task_v1.common import verify as previous
from qualified_path_v1.common import ROOT, PROJECT, RUN, SEEDS, read, save, sha
from qualified_path_v1.goal import WEIGHT


def main():
    prior = previous()
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')]
    paths.append(WEIGHT)
    for seed in SEEDS:
        paths.extend([PROJECT/f'qualified_task_v1/run/audit/{seed}/public_sensor.npz',
            PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/calibration.json',
            PROJECT/f'qualified_model_v1/run/sam/{seed}/prediction.npz',
            PROJECT/f'qualified_model_v1/run/{seed}/validated.json'])
    identities = dict(prior['identities'])
    identities.update({str(p): sha(p) for p in paths})
    save(RUN/'manifest.json', dict(identities=identities, seeds=SEEDS, max_sam_calls=2,
        max_task_attempts=0, max_training_runs=0, max_camera_search=0,
        scope='Observed placement and bounded static path preflight; no physical authorization'))
    print(dict(registered=2), flush=True)


if __name__ == '__main__':
    main()

"""唯一当前场景入口，只接受 baseline / varied_noisy。"""
import argparse
import os
from pathlib import Path
from pair_config import ROOT, SCENES, DEFAULT_SEED, configuration, item
from pair_runtime import bound
from pair_render import render
from sd_common import read, save, sha, verify
from sd_physics import execute, check_initial
from sd_render import probe


def audit_sensor(trace, config, *, index):
    if not trace:
        raise ValueError('No actual sensor frames recorded')
    for row in trace:
        assert row['attempt'] == index and row['scene_seed'] == config['seed']
        if config['group'] == 'baseline':
            assert row['clean_sha256'] == row['noisy_sha256']
            assert row['noise_rmse_m'] == 0 and row['dropped_pixels'] == 0
        else:
            assert row['clean_sha256'] != row['noisy_sha256']
            assert .0025 < row['noise_rmse_m'] < .0035
            assert .015 < row['dropout_fraction'] < .025
    return dict(passed=True, frames=len(trace), attempt=index)


def execution_audits(steps, config):
    rows = []
    for step in steps:
        record = read(step['result_path'])['records'][0]
        sensor = record['domain_randomization']
        assert sensor['level'] == config['group']
        rows.append(audit_sensor(sensor['sensor_frames'], config, index=step['index']))
    return rows


def run(task, folder):
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm for simulation'
    verify()
    config = configuration(task['seed'], task['group'])
    folder.mkdir(parents=True, exist_ok=False)
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch')]
    identities = {str(path): sha(path) for path in paths}
    save(folder/'configuration.json', config)
    save(folder/'identities.json', identities)
    static = probe(config, folder/'qualification')
    trace = render(config, folder/'preview')
    sensor_audit = audit_sensor(trace, config, index=1)
    seen = all(static['visibility'][task[k]]['qualified'] for k in ('source', 'destination'))
    qualified = (seen and static['calibration']['passed'] and config['geometry_accepted']
                 and config['compiled_check']['passed'])
    row = dict(item=task, qualified=qualified, status='qualification_rejected',
               success=False, steps=[], decisions=[], preview_sensor_audit=sensor_audit,
               model_calls=0, test_used=False, training_approved=False)
    if qualified:
        with bound(config):
            steps, decisions = execute(task, folder)
        row.update(status='executed', steps=steps, decisions=decisions, success=steps[-1]['success'],
                   initial_audit=check_initial(steps, config, static),
                   execution_sensor_audits=execution_audits(steps, config))
    assert all(sha(path) == digest for path, digest in identities.items())
    save(folder/'result.json', row)
    print(task['id'], row['status'], row['success'], flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description='原配置 / 全部变化＋深度噪声')
    parser.add_argument('--scene', choices=SCENES, required=True)
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--source', default='RedBlock')
    parser.add_argument('--destination', default='BlueBin')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    task = item(args.seed, args.scene, source=args.source, destination=args.destination)
    run(task, args.output.resolve())


if __name__ == '__main__':
    main()

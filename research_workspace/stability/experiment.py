"""冻结稳定网格物理对照；复用原执行器和规则反思。"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys

BASE = Path('/home/yeliheng/grasp_server/improvement_20261019/code')
OUT = Path('/home/yeliheng/grasp_server/stability_20261019')
THREADS = {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
SOURCES = ('RedBlock', 'GreenCylinder', 'PurpleCapsule', 'OrangeSphere')


def fingerprint():
    from geometry.experiment import fingerprints
    own = {name: hashlib.sha256((OUT/'stability'/name).read_bytes()).hexdigest()
           for name in ('detector.py', 'runtime.py', 'experiment.py', 'proposals.py', 'inference.py',
                        'monitor.py', 'kinematics.py', 'prepose.py')}
    return {'own': own, 'previous': fingerprints()}


def configuration(mode):
    seeds = [2000] if mode == 'train' else [5200, 5201]
    tasks = [dict(source=source, destination='BlueBin', fault=fault, seed=seed)
             for seed in seeds for source in SOURCES for fault in ('none', 'collision')]
    return {'tasks': tasks, 'arms': ['original', 'stable'], 'threads': THREADS,
            'fingerprint': fingerprint(), 'max_attempts': 3, 'scene_jitter': .012,
            'voxel_grid_origin': [0., 0., 0.], 'collision_threshold': .01, 'empty_threshold': .003}


def execute(task, arm, directory):
    os.chdir(BASE)
    sys.path.insert(0, str(BASE))
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.reflector import RuleReflector
    from stability.runtime import StableEngine
    path = Path(directory)
    if path.exists() and any(path.iterdir()):
        raise RuntimeError('Preserve partial output; use a new run directory')
    engine = StableEngine(stable=arm == 'stable', reflector=RuleReflector(), headless=True,
                          max_attempts=3, task_parser='rule', scene_jitter=.012)
    try:
        return engine.run(**task, method='reflection', output=path, context='stable-grid')
    finally:
        engine.close()


def compact(result, *, arm, case):
    first = result['records'][0]
    return dict(case=case, arm=arm, source=result['source'], fault=result['fault'], seed=result['seed'],
                success=result['success'], attempts=result['attempts'], first_success=first['accepted'],
                first_error=(first['error'] or {}).get('error_type'),
                last_error=(result['records'][-1]['error'] or {}).get('error_type'))


def run(config, directory):
    pending, rows = {}, []
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn')) as pool:
        for index, task in enumerate(config['tasks']):
            for arm in config['arms']:
                future = pool.submit(execute, task, arm, str(directory/f'{index:02d}'/arm))
                pending[future] = (index, arm)
        for future in as_completed(pending):
            index, arm = pending[future]
            rows.append(compact(future.result(), arm=arm, case=index))
            (directory/'progress.json').write_text(json.dumps(rows, indent=2))
            print(json.dumps(rows[-1]), flush=True)
    (directory/'result.json').write_text(json.dumps(rows, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['train', 'verify'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    assert all(os.environ.get(k) == v for k, v in THREADS.items())
    config, directory = configuration(args.mode), OUT/args.run
    manifest = directory/'manifest.json'
    if args.freeze:
        directory.mkdir(parents=True, exist_ok=True)
        with manifest.open('x') as stream:
            json.dump(config, stream, indent=2)
        return
    assert json.loads(manifest.read_text()) == config, 'Frozen configuration mismatch'
    (directory/'runtime.json').write_text(json.dumps({'job': os.environ.get('SLURM_JOB_ID'),
        'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'threads': THREADS}, indent=2))
    run(config, directory)


if __name__ == '__main__':
    main()

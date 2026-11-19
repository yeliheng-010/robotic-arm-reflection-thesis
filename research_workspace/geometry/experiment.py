"""固定数值线程的单/多候选规则策略配对实验。"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys

BASE = Path('/home/yeliheng/grasp_server/improvement_20261019/code')
OUT = Path('/home/yeliheng/grasp_server/geometry_20261019')
THREADS = {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
SOURCES = ('RedBlock', 'GreenCylinder', 'PurpleCapsule', 'OrangeSphere')
ARMS = ('single', 'multi')
MAX_ATTEMPTS, WORKERS = 3, 2
JITTER = .012


def fingerprints():
    from training.refine.validate import fingerprint
    own = {name: hashlib.sha256((OUT / 'geometry' / name).read_bytes()).hexdigest()
           for name in ('candidates.py', 'runtime.py', 'experiment.py')}
    return {'experiment': own, 'base': fingerprint()}


def configuration(mode):
    seed = 2000 if mode == 'train' else 4100
    tasks = [dict(source=s, destination='BlueBin', fault=f, seed=seed)
             for s in SOURCES for f in ('none', 'collision')
             if mode != 'train' or f == 'none' or s == 'GreenCylinder']
    return {'mode': mode, 'tasks': tasks, 'arms': list(ARMS), 'threads': THREADS,
            'max_attempts': MAX_ATTEMPTS, 'workers': WORKERS, 'scene_jitter': JITTER,
            'code_sha256': fingerprints(), 'policy': 'original preferred; extra yaw before unchanged filter',
            'collision_threshold': .01, 'empty_threshold': .003,
            'scope': 'simulation same families; no cross-family or LLM benefit claim'}


def execute(task, arm, directory):
    os.chdir(BASE)
    sys.path.insert(0, str(BASE))
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.reflector import RuleReflector
    from geometry.runtime import GeometryEngine
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError('Preserve existing run; choose a new output directory')
    engine = GeometryEngine(arm=arm, reflector=RuleReflector(), headless=True,
        max_attempts=MAX_ATTEMPTS, task_parser='rule', scene_jitter=JITTER)
    try:
        result = engine.run(**task, method='reflection', output=directory, context='geometry-comparison')
        return compact(result, arm=arm)
    finally:
        engine.close()


def compact(result, *, arm):
    first = result['records'][0]
    return {'source': result['source'], 'fault': result['fault'], 'seed': result['seed'],
            'arm': arm, 'success': result['success'], 'attempts': result['attempts'],
            'first_success': first['accepted'], 'first_error': (first['error'] or {}).get('error_type'),
            'last_error': (result['records'][-1]['error'] or {}).get('error_type')}


def run_pool(config, directory):
    pending, rows = {}, []
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
        for index, task in enumerate(config['tasks']):
            for arm in config['arms']:
                future = pool.submit(execute, task, arm, str(directory / f'{index:02d}' / arm))
                pending[future] = index
        for future in as_completed(pending):
            row = future.result()
            row['case'] = pending[future]
            rows.append(row)
            (directory / 'progress.json').write_text(json.dumps(rows, indent=2))
            print(json.dumps(row), flush=True)
    (directory / 'result.json').write_text(json.dumps(rows, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['train', 'holdout'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    assert all(os.environ.get(key) == value for key, value in THREADS.items())
    config = configuration(args.mode)
    directory = OUT / args.run
    manifest = directory / 'manifest.json'
    if args.freeze:
        directory.mkdir(parents=True, exist_ok=True)
        with manifest.open('x') as stream:
            json.dump(config, stream, indent=2)
        print(str(manifest))
        return
    if not manifest.exists() or json.loads(manifest.read_text()) != config:
        raise RuntimeError('Missing or changed frozen configuration')
    runtime = {'slurm_job': os.environ.get('SLURM_JOB_ID'),
               'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'threads': THREADS}
    (directory / 'runtime.json').write_text(json.dumps(runtime, indent=2))
    run_pool(config, directory)


if __name__ == '__main__':
    main()

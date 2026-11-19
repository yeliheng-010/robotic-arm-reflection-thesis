"""冻结独立实验；各物理运行在单独进程内，遥测不跨进程共享。"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import urllib.request

from decision.develop import BASE, OUT, TRAIN_IDS
from training.refine.validate import fingerprint as base_fingerprint

CODE = BASE / 'code'
COLLECTION = BASE.parent / 'overnight_20261019/collection'
ENDPOINT = 'http://127.0.0.1:18822'
MAX_ATTEMPTS = 3
HOLDOUT_SEED = 3100
SCENE_JITTER = .012
WORKERS = 2


def fingerprints():
    own = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT / 'decision').glob('*.py')}
    return {'decision': own, 'base': base_fingerprint()}


def tasks_for(mode):
    plan = json.loads((COLLECTION / 'plan.json').read_text())
    tasks = [dict(plan[index]) for index in TRAIN_IDS]
    assert all(t['split'] == 'train' for t in tasks)
    if mode == 'holdout':
        for task in tasks:
            task.update(seed=HOLDOUT_SEED, split='new_seed_holdout')
    return tasks


def configuration(mode):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(ENDPOINT + '/health', timeout=10) as response:
        teacher = json.load(response)
    assert teacher['architecture'] == 'qwen35' and teacher['adapter'] is None
    assert teacher['max_new_tokens'] == 256 and teacher['thinking'] is False
    arms = ['hybrid'] if mode == 'train' else ['retry', 'llm', 'rule', 'hybrid']
    return {'mode': mode, 'tasks': tasks_for(mode), 'arms': arms, 'teacher': teacher,
            'code_sha256': fingerprints(), 'endpoint': ENDPOINT, 'max_attempts': MAX_ATTEMPTS,
            'scene_jitter': SCENE_JITTER, 'workers': WORKERS,
            'boundary': 'Same task families at a new seed; no independent cross-family generalization claim'}


def reflector_for(arm, task, directory):
    from reflection.reflector import RuleReflector
    from training.refine.client import LocalTeacher
    from decision.selector import HybridSelector
    if arm == 'hybrid':
        return HybridSelector(task['instruction'], source=task['source'], endpoint=ENDPOINT,
                              audit_path=directory / 'choices.jsonl')
    if arm == 'llm':
        return LocalTeacher(task['instruction'], ENDPOINT)
    return RuleReflector() if arm == 'rule' else None


def execute(task, arm, directory):
    os.chdir(CODE)
    sys.path.insert(0, str(CODE))
    from reflection.__main__ import bootstrap
    bootstrap()
    from training.refine.engine import EvidenceEngine
    directory = Path(directory)
    saved = directory / 'result.json'
    if saved.exists():
        return json.loads(saved.read_text())
    # 不重复执行不完整轨迹，避免把不同生成混入同一个审计文件。
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError('Partial run exists; preserve it and choose a new run directory')
    engine = EvidenceEngine(reflector=reflector_for(arm, task, directory), headless=True,
                            max_attempts=MAX_ATTEMPTS, task_parser='rule', scene_jitter=SCENE_JITTER)
    try:
        return engine.run(**{k: v for k, v in task.items() if k != 'split'},
            method='retry' if arm == 'retry' else 'reflection', output=directory,
            context='decision-comparison-' + task['split'])
    finally:
        engine.close()


def compact(result, *, case, arm):
    return {'case': case, 'arm': arm, 'source': result['source'], 'fault': result['fault'],
            'success': result['success'], 'attempts': result['attempts'],
            'first_success': result['records'][0]['accepted'],
            'first_error': (result['records'][0]['error'] or {}).get('error_type'),
            'invalid': sum('reflection_error' in r for r in result['records'])}


def run_pool(config, directory):
    rows, pending = [], {}
    context = multiprocessing.get_context('spawn')
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=context) as pool:
        for index, task in enumerate(config['tasks']):
            for arm in config['arms']:
                case = f'{index:02d}'
                future = pool.submit(execute, task, arm, str(directory / case / arm))
                pending[future] = (case, arm)
        for future in as_completed(pending):
            case, arm = pending[future]
            row = compact(future.result(), case=case, arm=arm)
            rows.append(row)
            (directory / 'progress.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
            print(json.dumps(row, ensure_ascii=False), flush=True)
    (directory / 'result.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['train', 'holdout'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    directory = OUT / args.run
    config = configuration(args.mode)
    manifest = directory / 'manifest.json'
    if args.freeze:
        directory.mkdir(parents=True, exist_ok=True)
        with manifest.open('x') as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2)
        print(str(manifest))
        return
    if not manifest.exists() or json.loads(manifest.read_text()) != config:
        raise RuntimeError('Missing or changed frozen experiment configuration')
    run_pool(config, directory)


if __name__ == '__main__':
    main()


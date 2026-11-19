"""冻结配置后对验证种子做配对物理评估，不访问测试轨迹。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent
COLLECTION = OUT.parent / 'overnight_20261019/collection'
VALIDATION_IDS = (17, 25, 33, 137, 145, 153)


def fingerprint():
    directories = ('reflection', 'training/refine')
    paths = [p for directory in directories for p in (ROOT / directory).glob('*.py')]
    paths += [ROOT / 'grasp_process.py', ROOT / 'manipulator_grasp/env/ur5_grasp_env.py']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def verify_manifest(directory, config):
    path = directory / 'manifest.json'
    if not path.exists():
        raise RuntimeError('Validation manifest must be frozen before launch')
    if json.loads(path.read_text()) != config:
        raise RuntimeError('Frozen validation configuration/code/teacher changed')


def execute(task, arm, *, directory, endpoint):
    from training.refine.client import LocalTeacher
    from training.refine.engine import EvidenceEngine
    output = directory / arm
    if (output / 'result.json').exists():
        return json.loads((output / 'result.json').read_text())
    reflector = LocalTeacher(task['instruction'], endpoint) if arm == 'teacher' else None
    engine = EvidenceEngine(reflector=reflector, headless=True, max_attempts=3,
                            task_parser='rule', scene_jitter=.012)
    try:
        return engine.run(**{k: v for k, v in task.items() if k != 'split'},
                          method='reflection' if arm == 'teacher' else 'retry',
                          output=output, context='refine-validation-v1')
    finally:
        engine.close()


def compact(result, case, arm):
    return dict(case=case, arm=arm, source=result['source'], fault=result['fault'],
                success=result['success'], attempts=result['attempts'],
                first_success=result['records'][0]['accepted'],
                first_error=(result['records'][0].get('error') or {}).get('error_type'),
                invalid_reflections=sum('reflection_error' in r for r in result['records']))


def verify_pair(old, result):
    import numpy as np
    for field in ('source', 'destination', 'fault', 'seed', 'instruction', 'scene_jitter_m'):
        assert old[field] == result[field], field
    first, actual = old['records'][0], json.loads(json.dumps(result['records'][0]))
    for field in ('parameters', 'physical_success', 'accepted'):
        assert first[field] == actual[field], field
    for field in ('error_type', 'message'):
        assert first['error'][field] == actual['error'][field], field
    np.testing.assert_allclose(first['evaluation']['position'],
                               actual['evaluation']['position'], atol=1e-8, rtol=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:18821')
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    from reflection.__main__ import bootstrap
    bootstrap()
    directory = OUT / args.run
    plan = json.loads((COLLECTION / 'plan.json').read_text())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(args.endpoint + '/health', timeout=10) as response:
        teacher = json.load(response)
    config = dict(cases=list(VALIDATION_IDS), code_sha256=fingerprint(), teacher=teacher,
                  max_attempts=3, scene_jitter=.012, endpoint=args.endpoint,
                  selection='Frozen on training cases; validation is not an independent test')
    verify_manifest(directory, config)
    results = []
    for index in VALIDATION_IDS:
        task = plan[index]
        assert task['split'] == 'validation'
        case = f'{index:05d}'
        old = json.loads((COLLECTION / 'tasks' / case / 'result.json').read_text())
        results.append(compact(old, case, 'historical_teacher'))
        for arm in ('retry', 'teacher'):
            result = execute(task, arm, directory=directory / case, endpoint=args.endpoint)
            verify_pair(old, result)
            results.append(compact(result, case, arm))
            (directory / 'progress.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    (directory / 'result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()


"""原始冻结代码上的配对机制检查；规则输出不进入 LLM 样本池。"""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path('/home/yeliheng/grasp_server/overnight_20261019/code')
OUT = Path('/home/yeliheng/grasp_server/diagnosis_20261019')
COLLECTION = ROOT.parent / 'collection'
MAX_ATTEMPTS = 3
CASE_IDS = (0, 8, 16, 24, 32, 136, 144, 152)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configuration():
    manifest = json.loads((COLLECTION / 'manifest.json').read_text())
    for name, expected in manifest['code_sha256'].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Frozen code mismatch: ' + name)
    plan = json.loads((COLLECTION / 'plan.json').read_text())
    cases = []
    for index in CASE_IDS:
        task = plan[index]
        assert task['split'] == 'train'
        cases.append(dict(id=f'{index:05d}', task=task))
    return dict(cases=cases, max_attempts=MAX_ATTEMPTS, script_sha256=sha(Path(__file__)),
                code_sha256=manifest['code_sha256'], scene_jitter=0.012,
                provenance='diagnostic controls, not teacher-generated training data',
                baseline_sources=['OrangeSphere', 'PurpleCapsule'])


def run_case(case, arm):
    from reflection.engine import FeedbackEngine
    from reflection.reflector import RuleReflector

    output = OUT / 'controls' / case['id'] / arm
    if (output / 'result.json').exists():
        return json.loads((output / 'result.json').read_text())
    task = {k: v for k, v in case['task'].items() if k != 'split'}
    engine = FeedbackEngine(reflector=RuleReflector() if arm == 'rule' else None,
                            headless=True, task_parser='rule', perception='simulation',
                            segmentation='simulation', grasp_backend='geometric',
                            max_attempts=MAX_ATTEMPTS, scene_jitter=0.012)
    try:
        method = 'reflection' if arm == 'rule' else arm
        return engine.run(**task, method=method, output=output, context='diagnostic-controls-v1')
    finally:
        engine.close()


def summary(case, arm, result):
    output = (COLLECTION / 'tasks' / case['id'] if arm == 'historical_teacher'
              else OUT / 'controls' / case['id'] / arm)
    return dict(case=case['id'], arm=arm, fault=result['fault'], source=result['source'],
                success=result['success'], attempts=result['attempts'],
                errors=[(r.get('error') or {}).get('error_type') for r in result['records']],
                output=str(output))


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    from reflection.__main__ import bootstrap
    bootstrap()
    config = configuration()
    manifest = OUT / 'controls_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != config:
        raise RuntimeError('Probe configuration changed; use a new output directory')
    manifest.write_text(json.dumps(config, ensure_ascii=False, indent=2))
    results = []
    for case in config['cases']:
        historical = json.loads((COLLECTION / 'tasks' / case['id'] / 'result.json').read_text())
        results.append(summary(case, 'historical_teacher', historical))
        for arm in ('retry', 'rule'):
            result = run_case(case, arm)
            results.append(summary(case, arm, result))
            (OUT / 'controls_progress.json').write_text(json.dumps(results, indent=2))
    for source in config['baseline_sources']:
        case = dict(id='baseline_' + source, task=dict(source=source, destination='BlueBin',
                    fault='none', seed=2000))
        results.append(summary(case, 'baseline', run_case(case, 'baseline')))
    (OUT / 'controls_result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()


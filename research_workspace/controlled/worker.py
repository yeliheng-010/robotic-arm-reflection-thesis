"""每个方法在独立进程执行；保存真值轨迹与实际展示反馈。"""
import argparse
import json
import os
from pathlib import Path
from stability.experiment import BASE
from stability.collection_status import atomic
from controlled.config import ARMS, VERSION, MAX_ATTEMPTS, tasks, scenario

ROOT = Path('/home/yeliheng/grasp_server/controlled_v1')


def jsonlines(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def summary(result, directory, *, case, arm, task):
    records, events = result['records'], jsonlines(directory/'requests.jsonl')
    services = sum(bool(e.get('service_error')) for e in events)
    errors = sum('reflection_error' in r for r in records)
    return dict(case=case, arm=arm, task=task, success=result['success'],
                first_success=records[0]['accepted'], attempts=len(records),
                first_error=(records[0]['error'] or {}).get('error_type'),
                calls=sum('reflection' in r or 'reflection_error' in r for r in records),
                invalid_outputs=errors-services, service_errors=services,
                collision_attempts=sum((r['error'] or {}).get('error_type') == 'collision' for r in records),
                model_latency_s=sum(e['elapsed_s'] for e in events), elapsed_s=result['elapsed_s'])


def run(case, arm, *, run_name):
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.language import LABELS
    from reflection.reflector import RuleReflector
    from diversity.runtime import DiverseEngine
    from controlled.client import ControlledFlash
    from controlled.feedback import ProjectedReflector
    task = tasks()[case]
    config = scenario(task['seed'], task['level'])
    directory = ROOT/run_name/'tasks'/f'{case:02d}'/arm
    assert not directory.exists(), 'Preserve previous execution'
    instruction = f"把{LABELS[task['source']]}放进{LABELS[task['destination']]}"
    inner = ControlledFlash(instruction, directory) if arm == 'flash' else RuleReflector()
    reflector = ProjectedReflector(inner, config, directory=directory) if arm != 'retry' else None
    engine = DiverseEngine(scenario_config=config, reflector=reflector, max_attempts=MAX_ATTEMPTS,
                           headless=True, task_parser='rule')
    try:
        result = engine.run(source=task['source'], destination=task['destination'], fault=task['fault'],
                            seed=task['seed'], instruction=instruction, output=directory,
                            method='retry' if arm == 'retry' else 'reflection', context=VERSION)
    finally:
        engine.close()
    result.update(scenario=config, split=task['split'], test_used=False)
    atomic(directory/'result.json', result)
    row = summary(result, directory, case=case, arm=arm, task=task)
    atomic(directory/'summary.json', row)
    print(json.dumps(row), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, choices=range(48), required=True)
    parser.add_argument('--arm', choices=ARMS, required=True)
    parser.add_argument('--run', choices=('smoke', 'pilot'), required=True)
    args = parser.parse_args()
    os.chdir(BASE)
    run(args.case, args.arm, run_name=args.run)

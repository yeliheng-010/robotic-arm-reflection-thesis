"""独立进程执行随机场景，保留失败和每次传感器观测。"""
import argparse
import json
import os
from pathlib import Path
from stability.collection_status import atomic
from stability.experiment import BASE
from diversity.config import pilot_tasks, scenario

ROOT = Path('/home/yeliheng/grasp_server/diversity_v1/pilot')
ARMS = ('retry', 'flash')


def run(case, arm):
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.language import LABELS
    from flashnext.client import FlashReflector
    from diversity.runtime import DiverseEngine
    task = pilot_tasks()[case]
    config = scenario(task['seed'], task['level'])
    directory = ROOT/'tasks'/f'{case:02d}'/arm
    assert not directory.exists(), 'Preserve previous experiment'
    instruction = f"把{LABELS[task['source']]}放进{LABELS[task['destination']]}"
    reflector = FlashReflector(instruction, directory, max_tokens=1024) if arm == 'flash' else None
    engine = DiverseEngine(scenario_config=config, reflector=reflector, max_attempts=3,
                           headless=True, task_parser='rule')
    try:
        result = engine.run(source=task['source'], destination=task['destination'],
                            fault=task['fault'], seed=task['seed'], instruction=instruction,
                            output=directory, method='reflection' if arm == 'flash' else 'retry',
                            context='domain-randomization-v1')
    finally:
        engine.close()
    result.update(scenario=config, split=task['split'], test_used=False)
    atomic(directory/'result.json', result)
    records = result['records']
    summary = dict(case=case, arm=arm, task=task, success=result['success'], attempts=result['attempts'],
                   invalid=sum('reflection_error' in r for r in records),
                   calls=sum('reflection' in r or 'reflection_error' in r for r in records),
                   first_error=(records[0]['error'] or {}).get('error_type'))
    atomic(directory/'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, choices=range(16), required=True)
    parser.add_argument('--arm', choices=ARMS, required=True)
    args = parser.parse_args()
    os.chdir(BASE)
    run(args.case, args.arm)


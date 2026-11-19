"""一个开发场景的闭环执行，不修改历史实验的执行入口。"""
import argparse
import json
import os
from pathlib import Path
from stability.experiment import BASE
from stability.collection_status import atomic
from stability.loop_protocol import plan

ROOT = Path('/home/yeliheng/grasp_server/flashnext_v1/closed_loop1024')
ARMS = ('retry', 'rule', 'flash')


def run(case, arm):
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.language import LABELS
    from reflection.reflector import RuleReflector
    from stability.loop_worker import engine_class
    from flashnext.client import FlashReflector
    task = plan()[case]
    directory = ROOT/'tasks'/f'{case:02d}'/arm
    assert not directory.exists(), 'Preserve existing trajectories'
    instruction = f"把{LABELS[task['source']]}放进{LABELS[task['destination']]}"
    reflector = RuleReflector() if arm == 'rule' else None
    if arm == 'flash':
        reflector = FlashReflector(instruction, directory, max_tokens=1024)
    engine = engine_class()(reflector=reflector, max_attempts=3, headless=True,
                            task_parser='rule', scene_jitter=.012)
    try:
        result = engine.run(**task, instruction=instruction, output=directory,
                            method='retry' if arm == 'retry' else 'reflection',
                            context='flashnext-development-1024')
    finally:
        engine.close()
    path = directory/'requests.jsonl'
    events = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    records = result['records']
    summary = dict(case=case, arm=arm, task=task, success=result['success'],
                   attempts=result['attempts'], invalid=sum('reflection_error' in r for r in records),
                   calls=sum('reflection' in r or 'reflection_error' in r for r in records),
                   service_errors=sum(e.get('service_error', False) for e in events))
    atomic(directory/'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, choices=range(6), required=True)
    parser.add_argument('--arm', choices=ARMS, required=True)
    args = parser.parse_args()
    os.chdir(BASE)
    run(args.case, args.arm)


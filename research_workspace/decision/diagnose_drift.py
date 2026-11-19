"""仅复核训练场景数值差异，不用于模型选择或新种子调参。"""
import argparse
import json
import os
from pathlib import Path

from decision.experiment import CODE, COLLECTION, OUT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--case', type=int, choices=[32, 152], default=32)
    args = parser.parse_args()
    os.chdir(CODE)
    from reflection.__main__ import bootstrap
    bootstrap()
    from training.refine.engine import EvidenceEngine
    from threadpoolctl import threadpool_info
    task = json.loads((COLLECTION / 'plan.json').read_text())[args.case]
    directory = OUT / 'drift' / args.label
    engine = EvidenceEngine(headless=True, task_parser='rule', scene_jitter=.012)
    try:
        engine.run(**{k: v for k, v in task.items() if k != 'split'},
                   method='baseline', output=directory, context='training-numerical-reproduction')
    finally:
        engine.close()
    (directory / 'threads.json').write_text(json.dumps(threadpool_info(), indent=2))


if __name__ == '__main__':
    main()

"""每个完整搬运任务独立进程，四组共享同一物理引擎。"""
import argparse
import json
import os
from stability.experiment import BASE
from stability.loop_freeze import ROOT, verify
from stability.loop_protocol import ARMS
from stability.collection_status import atomic


def engine_class():
    from stability.runtime import StableEngine

    class EvaluationEngine(StableEngine):
        def _attempt(self, *args, **kwargs):
            record, report = super()._attempt(*args, **kwargs)
            record['candidate_trace']['source'] = 'geometric_proposals'
            count = len(record['candidate_trace'].get('returned', []))
            record['diagnostics']['available_candidate_count'] = count
            record['diagnostics']['selected_candidate_index'] = (
                min(record['parameters']['candidate_index'], count-1) if count else None)
            if report is not None:
                report.evidence['diagnostics'] = record['diagnostics']
                record['error'] = report.to_dict()
            return record, report
    return EvaluationEngine


def run(case, arm):
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.language import LABELS
    from reflection.reflector import RuleReflector
    from stability.loop_client import LoopReflector
    config = verify()
    task, directory = config['tasks'][case], ROOT/'tasks'/f'{case:02d}'/arm
    assert not directory.exists(), 'Preserve prior execution'
    instruction = f"把{LABELS[task['source']]}放进{LABELS[task['destination']]}"
    reflector = RuleReflector() if arm == 'rule' else None
    if arm in ('base', 'adapted'):
        reflector = LoopReflector(instruction, directory, arm=arm)
    engine = engine_class()(reflector=reflector, max_attempts=3, headless=True,
        task_parser='rule', scene_jitter=.012)
    try:
        result = engine.run(**task, instruction=instruction, output=directory,
            method='retry' if arm == 'retry' else 'reflection', context='closed-loop-development')
    finally:
        engine.close()
    events = [json.loads(s) for s in (directory/'requests.jsonl').read_text().splitlines()] if arm in ('base', 'adapted') else []
    invalid = sum('reflection_error' in r for r in result['records'])
    calls = sum('reflection' in r or 'reflection_error' in r for r in result['records'])
    atomic(directory/'summary.json', dict(case=case, arm=arm, task=task, success=result['success'],
        attempts=result['attempts'], calls=calls, invalid=invalid,
        service_errors=sum(e.get('service_error', False) for e in events), result=str(directory/'result.json')))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, required=True)
    parser.add_argument('--arm', choices=ARMS, required=True)
    args = parser.parse_args()
    os.chdir(BASE)
    run(args.case, args.arm)


if __name__ == '__main__':
    main()

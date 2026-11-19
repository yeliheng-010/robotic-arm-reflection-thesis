"""一个方法、一次重复一个进程，失败保留。"""
import argparse
import os
from stability.experiment import BASE
from stability.collection_status import atomic
from controlled.config import tasks, scenario, MAX_ATTEMPTS
from controlled.worker import summary, jsonlines
from refinement.config import ROOT, ARMS, run_id
from refinement.freeze import verify


def run(item, mode):
    verify()
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.language import LABELS
    from reflection.reflector import RuleReflector
    from diversity.runtime import DiverseEngine
    from controlled.feedback import ProjectedReflector
    from refinement.policy import BoundedRule
    from refinement.client import SemanticFlash
    from refinement.audit import audit_run
    task, arm = tasks()[item['case']], item['arm']
    config = scenario(task['seed'], task['level'])
    directory = ROOT/mode/'tasks'/run_id(item)
    assert not directory.exists(), 'Preserve prior execution'
    instruction = f"把{LABELS[task['source']]}放进{LABELS[task['destination']]}"
    if arm.startswith('flash'):
        inner = SemanticFlash(instruction, directory, variant=arm)
    else:
        inner = BoundedRule() if arm == 'rule_new' else RuleReflector()
    reflector = ProjectedReflector(inner, config, directory=directory)
    engine = DiverseEngine(scenario_config=config, reflector=reflector, max_attempts=MAX_ATTEMPTS,
                           headless=True, task_parser='rule')
    try:
        result = engine.run(source=task['source'], destination=task['destination'], fault=task['fault'],
                            seed=task['seed'], instruction=instruction, output=directory,
                            method='reflection', context='refinement_v2')
    finally:
        engine.close()
    result.update(scenario=config, split=task['split'], test_used=False, method_variant=arm)
    atomic(directory/'result.json', result)
    row = summary(result, directory, case=item['case'], arm=arm, task=task)
    row['policy_exhausted'] = sum('PolicyExhausted' in e.get('error', '')
                                  for e in jsonlines(directory/'feedback.jsonl'))
    row['invalid_outputs'] -= row['policy_exhausted']
    row.update(repeat=item['repeat'], audit=audit_run(directory, result, item))
    atomic(directory/'summary.json', row)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, required=True)
    parser.add_argument('--arm', choices=ARMS, required=True)
    parser.add_argument('--repeat', type=int, required=True)
    parser.add_argument('--mode', choices=('smoke', 'regression'), required=True)
    args = vars(parser.parse_args())
    mode = args.pop('mode')
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    os.chdir(BASE)
    run(args, mode)

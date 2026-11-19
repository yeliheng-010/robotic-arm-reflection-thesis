"""开发条件中的同预算闭环；三次尝试，四种独立方法。"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from stability.collection_status import atomic
from controlled.config import tasks,scenario,MAX_ATTEMPTS
from controlled.worker import summary,jsonlines
from controlled.audit import audit_records
from refinement.audit import compare_saved,emitted
from refinement.config import SIM_PYTHON,WORKER_TIMEOUT
from bounded.protocol import ROOT,verify,CASES
from bounded.candidates import candidates
from bounded.selection import payload,resolve


def audit(directory,result,item):
    from controlled.feedback import project_report
    audit_records(result,item['task'])
    original = ROOT.parent/'controlled_v3/pilot/tasks'/f"{item['case']:02d}"/'retry/result.json'
    compare_saved(result,json.loads(original.read_text()))
    events = jsonlines(directory/'feedback.jsonl')
    selected = jsonlines(directory/'selection.jsonl') if item['arm']=='hybrid' else jsonlines(directory/'baseline_choices.jsonl')
    calls = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    assert len(calls)==len(events)==len(selected)
    history = []
    for record,event,choice in zip(calls,events,selected):
        projected = project_report(record['error'],result['scenario'],attempt=record['attempt'])
        assert event['projected']==projected and event['history']==history
        rows = candidates(emitted(projected),record['parameters'],history)
        assert rows==choice['candidates']
        if item['arm']=='hybrid':
            assert choice['request']==payload(emitted(projected),record['parameters'],rows=rows,history=history)
            if 'reflection' in record:
                assert resolve(choice['text'],rows)==record['reflection']==event['answer']
        elif 'reflection' in record:
            assert choice['answer']==record['reflection']==event['answer']
        if 'reflection' in record:
            history.append({'error':projected,'reflection':record['reflection']})
    return dict(passed=True,initial_paired=True,projected_only=True,executed_actions_verified=True,calls=len(calls))


def worker(index):
    from reflection.__main__ import bootstrap
    bootstrap()
    from diversity.runtime import DiverseEngine
    from controlled.feedback import ProjectedReflector
    from bounded.client import HybridSelector
    from bounded.baselines import CandidateBaseline
    item = verify()['closed_loop'][index]
    task = tasks()[item['case']]
    directory = ROOT/'physical/tasks'/item['id']
    assert not directory.exists()
    config = scenario(task['seed'],task['level'])
    if item['arm']=='hybrid':
        inner = HybridSelector(directory)
    else:
        inner = CandidateBaseline(directory,mode=item['arm'],seed=904250+item['case'])
    reflector = ProjectedReflector(inner,config,directory=directory) if item['arm']!='retry' else None
    engine = DiverseEngine(scenario_config=config,reflector=reflector,max_attempts=MAX_ATTEMPTS,
                           headless=True,task_parser='rule')
    try:
        result = engine.run(**{k:task[k] for k in ('source','destination','fault','seed')},output=directory,
                            method='retry' if item['arm']=='retry' else 'reflection',context='bounded_hybrid_v1')
    finally:
        engine.close()
    result = json.loads(json.dumps(result))
    result.update(scenario=config,split='train',test_used=False,method_variant=item['arm'],training_approved=False)
    atomic(directory/'result.json',result)
    row = summary(result,directory,case=item['case'],arm=item['arm'],task=task)
    row.update(repeat=item['repeat'],audit=audit(directory,result,dict(item,task=task)))
    row['service_errors'] = sum(bool(e.get('service_error')) for e in jsonlines(directory/'selection.jsonl'))
    atomic(directory/'summary.json',row)


def run(shard):
    protocol = verify()
    gate = json.loads((ROOT/'semantic/result.json').read_text())
    assert gate['status']=='completed' and gate['gate_passed'], 'Synthetic gate not passed'
    root = ROOT/'physical'
    root.mkdir(exist_ok=True)
    directory = root/f'shard_{shard}'
    directory.mkdir(exist_ok=False)
    order = [(i,r) for i,r in enumerate(protocol['closed_loop']) if CASES.index(r['case'])%2==shard]
    result = dict(status='running',expected=len(order),completed=0,rows=[],started_at=time.time(),job=os.environ['SLURM_JOB_ID'])
    try:
        for index,item in order:
            with (root/(item['id']+'.log')).open('x') as stream:
                subprocess.run([SIM_PYTHON,'-m','bounded.physical','--index',str(index)],
                               stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=WORKER_TIMEOUT)
            row = json.loads((root/'tasks'/item['id']/'summary.json').read_text())
            result['rows'].append(row)
            result['completed'] += 1
            atomic(directory/'progress.json',result)
            assert not row['service_errors'], 'Model service error'
        verify()
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed',error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(directory/'result.json',result)
        atomic(directory/'progress.json',result)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index',type=int)
    parser.add_argument('--shard',type=int,choices=(0,1))
    args = parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    run(args.shard) if args.index is None else worker(args.index)

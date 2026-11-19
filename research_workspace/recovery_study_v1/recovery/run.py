"""通过Slurm执行预登记清单；冒烟结果只审计复用，不重新采样。"""
import argparse
from contextlib import nullcontext
import json
import os
import subprocess
import time
from stability.collection_status import atomic
from refinement.config import SIM_PYTHON,WORKER_TIMEOUT
from recovery.protocol import ROOT,verify
from recovery.design import configuration,MAX_ATTEMPTS,smoke_ids
from recovery.references import collision_context
from recovery.feedback import FeedbackAdapter
from recovery.methods import make
from recovery.audit import audit

SHARDS = 2


def worker(index):
    from reflection.__main__ import bootstrap
    bootstrap()
    from diversity.runtime import DiverseEngine
    from reflection.language import LABELS
    item = verify()['items'][index]
    directory = ROOT/'tasks'/item['id']
    assert not directory.exists(), 'Preserve prior output'
    config = configuration(item)
    instruction = f"把{LABELS[item['source']]}放进{LABELS[item['destination']]}"
    inner = make(item,directory,instruction=instruction)
    reflector = FeedbackAdapter(inner,config,directory=directory) if inner else None
    engine = DiverseEngine(scenario_config=config,reflector=reflector,max_attempts=MAX_ATTEMPTS,
                           headless=True,task_parser='rule')
    trace = dict(steps=0,source_path=[],divider_contacts={})
    context = collision_context(dict(item,enabled=True),trace) if item['study']=='collision' else nullcontext()
    try:
        with context:
            result = engine.run(**{k:item[k] for k in ('source','destination','fault','seed')},
                                instruction=instruction,output=directory,
                                method='reflection' if reflector else 'retry',context='recovery_study_v1')
    finally:
        engine.close()
    result = json.loads(json.dumps(result))
    result.update(scenario=config,item=item,test_used=False,training_approved=False,split='train')
    atomic(directory/'result.json',result)
    if item['study']=='collision':
        atomic(directory/'collision_trace.json',trace)
    verified = audit(directory,result,item)
    row = dict(id=item['id'],study=item['study'],arm=item['arm'],mode=item.get('mode'),
               scene_id=item.get('scene_id'),success=result['success'],attempts=result['attempts'],
               elapsed_s=result['elapsed_s'],audit=verified,**{k:v for k,v in verified.items() if k!='passed'})
    atomic(directory/'summary.json',row)


def execute(index,item):
    directory = ROOT/'tasks'/item['id']
    if (directory/'summary.json').exists():
        result = json.loads((directory/'result.json').read_text())
        verified = audit(directory,result,item)
        row = json.loads((directory/'summary.json').read_text())
        assert row['audit']==verified and row['success']==result['success']
        return row
    with (ROOT/'logs'/f"{item['id']}.log").open('x') as stream:
        subprocess.run([SIM_PYTHON,'-m','recovery.run','--index',str(index)],stdout=stream,
                       stderr=subprocess.STDOUT,check=True,timeout=WORKER_TIMEOUT)
    return json.loads((directory/'summary.json').read_text())


def smoke_gate():
    for shard in range(SHARDS):
        saved = json.loads((ROOT/'smoke'/f'shard_{shard}'/'progress.json').read_text())
        assert saved['status']=='completed' and saved['completed']==1
        assert all(not r['service_errors'] for r in saved['rows'])


def run(phase,shard):
    from flashnext.client import ready
    items = verify()['items']
    if phase=='batch':
        smoke_gate()
    order = [(i,r) for i,r in enumerate(items) if i%SHARDS==shard]
    if phase=='smoke':
        order = [(i,r) for i,r in enumerate(items) if r['id']==smoke_ids()[shard]]
    output = ROOT/phase/f'shard_{shard}'
    output.mkdir(parents=True,exist_ok=False)
    (ROOT/'logs').mkdir(exist_ok=True)
    status = dict(status='running',expected=len(order),completed=0,rows=[],started_at=time.time(),
                  job=os.environ['SLURM_JOB_ID'],array_job=os.environ.get('SLURM_ARRAY_JOB_ID'),models=ready())
    atomic(output/'progress.json',status)
    try:
        for index,item in order:
            row = execute(index,item)
            status['rows'].append(row)
            status['completed'] += 1
            atomic(output/'progress.json',status)
            assert not row['service_errors'], 'Model service error; preserve run and stop'
        verify()
        status['status'] = 'completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at'] = time.time()
        atomic(output/'progress.json',status)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index',type=int)
    parser.add_argument('--phase',choices=('smoke','batch'))
    parser.add_argument('--shard',type=int,choices=range(SHARDS))
    args = parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    worker(args.index) if args.index is not None else run(args.phase,args.shard)

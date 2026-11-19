"""每个固定参数使用独立进程，所有结果保留。"""
import argparse
import json
import os
import subprocess
import time
from stability.collection_status import atomic
from refinement.config import SIM_PYTHON,WORKER_TIMEOUT
from recovery.references import collision_context
from semanticfix2.protocol import ROOT,verify
from semanticfix2.design import configuration
from semanticfix2.audit import audit

SHARDS = 2


def worker(index):
    from semanticfix2.engine import fixed_engine
    item = verify()['items'][index]
    directory = ROOT/'physical/tasks'/item['id']
    assert not directory.exists(), 'Preserve previous execution'
    config = configuration(item)
    engine = fixed_engine(item['parameters'])(scenario_config=config,max_attempts=1,headless=True,task_parser='rule')
    trace = dict(steps=0,source_path=[],divider_contacts={})
    try:
        with collision_context(dict(item,enabled=True),trace):
            result = engine.run(source=item['source'],destination=item['destination'],seed=item['seed'],
                                fault='none',output=directory,method='retry',context='semantic_geometry_diagnostic')
    finally:
        engine.close()
    result = json.loads(json.dumps(result))
    result.update(item=item,scenario=config,test_used=False,training_approved=False,source='fixed_diagnostic_intervention')
    atomic(directory/'result.json',result)
    record = result['records'][0]
    error = record.get('error') or {}
    row = dict(id=item['id'],scene_id=item['scene_id'],variant=item['variant'],success=result['success'],
               error=error.get('error_type'),phase=error.get('evidence',{}).get('motion_context',{}).get('phase'),
               elapsed_s=result['elapsed_s'],audit=audit(result,item),model_calls=0)
    atomic(directory/'summary.json',row)


def execute(index,item):
    directory = ROOT/'physical/tasks'/item['id']
    if (directory/'summary.json').exists():
        result = json.loads((directory/'result.json').read_text())
        row = json.loads((directory/'summary.json').read_text())
        assert row['audit']==audit(result,item)
        return row
    with (ROOT/'physical'/f"{item['id']}.log").open('x') as stream:
        subprocess.run([SIM_PYTHON,'-m','semanticfix2.run','--index',str(index)],stdout=stream,
                       stderr=subprocess.STDOUT,check=True,timeout=WORKER_TIMEOUT)
    return json.loads((directory/'summary.json').read_text())


def run(phase,shard):
    protocol = verify()
    factors = ('position_only','yaw_only')
    order = [(i,r) for i,r in enumerate(protocol['items']) if r['factor']==factors[shard]]
    if phase=='smoke':
        order = [(i,r) for i,r in order if r['variant']=='default']
    else:
        for index in range(SHARDS):
            status = json.loads((ROOT/'smoke'/f'shard_{index}'/'progress.json').read_text())
            assert status['status']=='completed' and status['completed']==1
    (ROOT/'physical').mkdir(exist_ok=True)
    output = ROOT/phase/f'shard_{shard}'
    output.mkdir(parents=True,exist_ok=False)
    status = dict(status='running',completed=0,expected=len(order),rows=[],started_at=time.time(),job=os.environ['SLURM_JOB_ID'])
    atomic(output/'progress.json',status)
    try:
        for index,item in order:
            status['rows'].append(execute(index,item))
            status['completed'] += 1
            atomic(output/'progress.json',status)
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

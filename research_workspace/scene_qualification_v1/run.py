"""每个条件先控制后处理；不合格条件保留而不补采。"""
import argparse
import json
import os
import subprocess
import time
from unittest.mock import patch
import numpy as np
from stability.collection_status import atomic
from refinement.config import SIM_PYTHON,WORKER_TIMEOUT
from design import build,qualify
from protocol import ROOT,verify,reference


def execute_arm(item,enabled):
    from diversity.runtime import DiverseEngine
    directory = ROOT/'runs'/item['id']/str(int(enabled))
    assert not directory.exists()
    config = build(item['seed'],item['factor'])
    trace = dict(steps=0,source_path=[],divider_contacts={})
    engine = DiverseEngine(scenario_config=config,max_attempts=1,headless=True,task_parser='rule')
    try:
        with reference.context(dict(item,enabled=enabled),trace):
            result = engine.run(source=item['source'],destination=item['destination'],seed=item['seed'],
                                fault='none',method='retry',output=directory,context='scene_qualification_v1')
    finally:
        engine.close()
    result.update(scenario=config,test_used=False,source='scene_control',training_approved=False)
    atomic(directory/'result.json',result)
    record = result['records'][0]
    error = record.get('error') or {}
    contacts = error.get('evidence',{}).get('contacts',[])
    row = dict(enabled=enabled,success=result['success'],error=error.get('error_type'),
               segment=record.get('diagnostics',{}).get('motion_segment'),contacts=contacts,
               intended_collision=error.get('error_type')=='collision' and any('SafetyDivider' in p for p in contacts),
               trace=trace)
    atomic(directory/'summary.json',row)
    return row


def worker(index):
    item = verify()['items'][index]
    directory = ROOT/'runs'/item['id']
    directory.mkdir(parents=True,exist_ok=False)
    with patch.object(reference,'scenario',lambda seed,group:build(seed,item['factor'])):
        geometry = reference.geometry_check(dict(item,enabled=True))
    row = dict(item=item,geometry=geometry,qualified=False,executed=0,planned=2,test_used=False)
    if not geometry['passed']:
        row['status'] = 'geometry_ineligible'
    else:
        control = execute_arm(item,False)
        row.update(control=control,executed=1,status='not_run_control_failed')
        if control['success']:
            treatment = execute_arm(item,True)
            for field in ('initial_qpos','initial_body_xyz'):
                np.testing.assert_allclose(control['trace'][field],treatment['trace'][field],atol=1e-8,rtol=0)
            ok = qualify(control['success'],treatment['intended_collision'],treatment['segment'],paired=True)
            row.update(treatment=treatment,executed=2,status='paired',paired=True,qualified=ok)
    atomic(directory/'pair.json',row)


def run(shard):
    protocol = verify()
    output = ROOT/f'shard_{shard}'
    output.mkdir(exist_ok=False)
    order = [(i,r) for i,r in enumerate(protocol['items']) if i%2==shard]
    result = dict(status='running',expected=6,planned_runs=12,completed=0,rows=[],started_at=time.time(),job=os.environ['SLURM_JOB_ID'])
    try:
        for index,item in order:
            with (ROOT/(item['id']+'.log')).open('x') as stream:
                subprocess.run([SIM_PYTHON,str(ROOT/'run.py'),'--index',str(index)],stdout=stream,
                               stderr=subprocess.STDOUT,check=True,timeout=WORKER_TIMEOUT)
            result['rows'].append(json.loads((ROOT/'runs'/item['id']/'pair.json').read_text()))
            result['completed'] += 1
            atomic(output/'progress.json',result)
        verify()
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed',error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(output/'result.json',result)
        atomic(output/'progress.json',result)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index',type=int)
    parser.add_argument('--shard',type=int,choices=(0,1))
    args = parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    run(args.shard) if args.index is None else worker(args.index)

"""新布局的固定障碍校准，包含完整分母和运行初态配对。"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from stability.collection_status import atomic
from refinement.freeze import verify as verify_previous
from refinement.config import SIM_PYTHON, WORKER_TIMEOUT
from controlled.config import scenario

ROOT = Path('/home/yeliheng/grasp_server/collision_validation_v1')
SEEDS = (904241, 904242, 904243)
PAIRS = (('RedBlock','BlueBin'), ('PurpleCapsule','RedBin'))
GEOMETRY = {'RedBlock': ([1.20,.355,.74],[.34,.012,.19]),
            'PurpleCapsule': ([1.3575,.84,.74],[.0375,.012,.19])}
MIN_CLEARANCE = .008
SETTLE_STEPS = 500


def items():
    return [dict(id=f'C{p}_{seed}_{int(enabled)}', source=source, destination=dest,
                 seed=seed, enabled=enabled)
            for p,(source,dest) in enumerate(PAIRS) for seed in SEEDS for enabled in (False,True)]


def edit_geometry(spec, item):
    center, size = GEOMETRY[item['source']]
    spec.body('SafetyDivider').pos = center
    geom = spec.geom('safety_divider')
    geom.size = size
    geom.pos = [0,0,size[2]]
    if not item['enabled']:
        geom.contype, geom.conaffinity = 0,0
        geom.rgba = [0,0,0,0]
    for suffix in ('left','right'):
        spec.geom('safety_divider_marker_'+suffix).rgba = [0,0,0,0]


def geometry_check(item):
    import mujoco
    from diversity.scene import ScenarioFault
    from reflection.fault_injection import Fault
    from reflection.monitors import object_extents
    path = ROOT.parent/'improvement_20261019/code/manipulator_grasp/assets/scenes/scene.xml'
    spec = mujoco.MjSpec.from_file(str(path))
    ScenarioFault(Fault('none'),scenario(item['seed'],'layout')).model_editor(spec)
    edit_geometry(spec,item)
    model = spec.compile()
    data = mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    center,size = map(np.array, GEOMETRY[item['source']])
    low,high = center-size,center+size
    low[2],high[2] = center[2],center[2]+2*size[2]
    rows = []
    for index in range(1,model.nbody):
        body = model.body(index)
        if body.geomnum == 0 or body.name in ('SafetyDivider','simple_table'):
            continue
        start,count = int(model.body_geomadr[index]),int(model.body_geomnum[index])
        if not np.any(model.geom_contype[start:start+count] | model.geom_conaffinity[start:start+count]):
            continue
        body_low,body_high = object_extents(model,data,index)
        rows.append(dict(body=body.name,clearance=float(max(np.maximum(low-body_high,body_low-high)))))
    blockers = [r for r in rows if r['clearance'] < MIN_CLEARANCE]
    return dict(passed=not blockers,blockers=blockers,rows=rows,
                scope='compiled default qpos; runtime settled qpos checked separately')


def configuration():
    previous = verify_previous()
    code = {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'calibrate.py',ROOT/'run.sbatch')}
    return dict(previous=previous,code=code,items=items(),geometry=GEOMETRY,
                clearance=MIN_CLEARANCE,test_used=False,training_approved=False)


def verify():
    expected = json.loads((ROOT/'protocol.json').read_text())
    assert expected == json.loads(json.dumps(configuration())), 'Protocol drift'


@contextmanager
def context(item,trace):
    from diversity.scene import ScenarioFault
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    from refinement.collision import observe_step
    original_edit,original_step = ScenarioFault.model_editor,UR5GraspEnv.step

    def edit(fault,spec):
        original_edit(fault,spec)
        edit_geometry(spec,item)

    def capture(env,*args,**kwargs):
        value = original_step(env,*args,**kwargs)
        if trace['steps'] == SETTLE_STEPS-1:
            trace['initial_qpos'] = env.mj_data.qpos.tolist()
            trace['initial_body_xyz'] = env.mj_data.xpos.tolist()
        return value

    with patch.object(ScenarioFault,'model_editor',edit), patch.object(
            UR5GraspEnv,'step',observe_step(capture,trace,item['source'])):
        yield


def worker(index):
    from diversity.runtime import DiverseEngine
    verify()
    item = items()[index]
    directory = ROOT/'runs'/item['id']
    directory.mkdir(parents=True,exist_ok=False)
    geometry = geometry_check(item)
    atomic(directory/'geometry.json',geometry)
    if not geometry['passed']:
        atomic(directory/'summary.json',dict(item=item,status='geometry_ineligible',success=False,
               intended_collision=False,geometry=geometry,test_used=False))
        return
    trace = dict(steps=0,source_path=[],divider_contacts={})
    engine = DiverseEngine(scenario_config=scenario(item['seed'],'layout'),max_attempts=1,
                           headless=True,task_parser='rule')
    try:
        with context(item,trace):
            result = engine.run(source=item['source'],destination=item['destination'],seed=item['seed'],
                                fault='none',method='retry',output=directory,context='collision_validation_v1')
    finally:
        engine.close()
    record = result['records'][0]
    error = record.get('error') or {}
    contacts = error.get('evidence',{}).get('contacts',[])
    collision = error.get('error_type')=='collision' and any('SafetyDivider' in p for p in contacts)
    row = dict(item=item,status='executed',success=result['success'],error=error.get('error_type'),
               intended_collision=collision,diagnostics=record.get('diagnostics'),trace=trace,test_used=False)
    if item['enabled']:
        baseline = json.loads((ROOT/'runs'/items()[index-1]['id']/'summary.json').read_text())
        assert baseline['status']=='executed'
        for field in ('initial_qpos','initial_body_xyz'):
            np.testing.assert_allclose(baseline['trace'][field],trace[field],atol=1e-8,rtol=0)
        row['paired_initial_state'] = True
        segment = (row['diagnostics'] or {}).get('motion_segment')
        row['qualified_injection'] = baseline['success'] and collision and segment in ('lift','transport')
    atomic(directory/'summary.json',row)


def run():
    verify()
    assert not (ROOT/'progress.json').exists()
    result = dict(status='running',expected=12,completed=0,rows=[],started_at=time.time(),
                  job=os.environ['SLURM_JOB_ID'],model_calls=0,test_used=False)
    atomic(ROOT/'progress.json',result)
    try:
        for index,item in enumerate(items()):
            with (ROOT/(item['id']+'.log')).open('x') as stream:
                subprocess.run([SIM_PYTHON,str(ROOT/'calibrate.py'),'--index',str(index)],
                               stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=WORKER_TIMEOUT)
            result['rows'].append(json.loads((ROOT/'runs'/item['id']/'summary.json').read_text()))
            result['completed'] = len(result['rows'])
            atomic(ROOT/'progress.json',result)
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed',error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(ROOT/'result.json',result)
        atomic(ROOT/'progress.json',result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--index',type=int)
    args = parser.parse_args()
    if args.freeze:
        with (ROOT/'protocol.json').open('x') as stream:
            json.dump(configuration(),stream,indent=2)
        atomic(ROOT/'preflight.json',{i['id']:geometry_check(i) for i in items()})
    else:
        assert os.environ.get('SLURM_JOB_ID'),'Use Slurm'
        run() if args.index is None else worker(args.index)

"""针对未穿过旧障碍的紫色胶囊路线做独立默认策略校准。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from unittest.mock import patch
import numpy as np
from stability.collection_status import atomic
from refinement.freeze import verify
from refinement.config import SIM_PYTHON, WORKER_TIMEOUT
from geometry_check import BODY_X, HALF_X, inspect

ROOT = Path('/home/yeliheng/grasp_server/collision_route_v3')
HEIGHTS = (None, .06, .12, .15, .19, .22)
BODY_Y = .84
CASE = 24
DIVIDER_HALF_WIDTH_Y = .012
MIN_CLEARANCE = .008


def protocol():
    from diversity.config import SLOTS, RADII
    clearances = [abs(BODY_Y-xy[1])-radius-DIVIDER_HALF_WIDTH_Y for xy, radius in zip(SLOTS, RADII)]
    assert min(clearances) >= MIN_CLEARANCE, 'Divider intersects existing object footprint'
    # 红箱前壁最低 Y=1.03-0.12-0.012=0.898，确保障碍与箱壁分离。
    assert .898-(BODY_Y+DIVIDER_HALF_WIDTH_Y) >= MIN_CLEARANCE
    return dict(heights=HEIGHTS, body_y=BODY_Y, body_x=BODY_X, half_x=HALF_X,
                case=CASE, attempts=1, model_calls=0,
                initial_object_clearances_m=clearances,
                code={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (ROOT/'calibrate.py', ROOT/'run.sbatch', ROOT/'geometry_check.py', ROOT/'geometry_check.json')},
                reason='Original source trajectory stays at y>=0.453 while divider is at y=0.355',
                selection='Default-policy intended obstacle contact only; all controls retained')


def check_protocol():
    verify()
    assert json.loads((ROOT/'protocol.json').read_text()) == json.loads(json.dumps(protocol()))


def run_one(index):
    from reflection.__main__ import bootstrap
    bootstrap()
    from diversity.runtime import DiverseEngine
    from diversity.scene import ScenarioFault
    from controlled.config import tasks, scenario
    from refinement.collision import challenge
    task, height = tasks()[CASE], HEIGHTS[index]
    directory = ROOT/'runs'/str(index)
    assert not directory.exists()
    original = ScenarioFault.model_editor

    def relocate(fault, spec):
        original(fault, spec)
        body = spec.body('SafetyDivider')
        body.pos = [BODY_X, BODY_Y, body.pos[2]]
        geom = spec.geom('safety_divider')
        geom.size = [HALF_X, geom.size[1], geom.size[2]]
        for suffix in ('left', 'right'):
            spec.geom('safety_divider_marker_'+suffix).rgba = [0., 0., 0., 0.]

    trace = dict(steps=0, source_path=[], divider_contacts={})
    engine = DiverseEngine(scenario_config=scenario(task['seed'], 'clean'), max_attempts=1,
                           headless=True, task_parser='rule')
    try:
        with patch.object(ScenarioFault, 'model_editor', relocate), challenge(height, trace, task['source']):
            result = engine.run(source=task['source'], destination=task['destination'], seed=task['seed'],
                                fault='none', output=directory, method='retry', context='collision_route_v3')
    finally:
        engine.close()
    record = result['records'][0]
    original_path = ROOT.parent/'refinement_v2/collision/24_0/result.json'
    baseline = json.loads(original_path.read_text())['records'][0]
    np.testing.assert_allclose(baseline['candidate_trace']['initial_qpos'],
                               record['candidate_trace']['initial_qpos'], atol=1e-8, rtol=0)
    assert trace['geometry']['center'][1] == BODY_Y
    error = record['error'] or {}
    contacts = error.get('evidence', {}).get('contacts', [])
    triggered = error.get('error_type') == 'collision' and any('SafetyDivider' in pair for pair in contacts)
    row = dict(index=index, height=height, body_y=BODY_Y, success=result['success'],
               error=error.get('error_type'), intended_collision=triggered, contacts=contacts,
               diagnostics=record.get('diagnostics'), trace=trace, initial_qpos_verified=True)
    atomic(directory/'summary.json', row)


def run():
    check_protocol()
    assert not (ROOT/'progress.json').exists()
    result = dict(status='running', expected=len(HEIGHTS), rows=[], started_at=time.time(),
                  job=os.environ['SLURM_JOB_ID'], test_used=False, model_calls=0)
    atomic(ROOT/'progress.json', result)
    try:
        for index in range(len(HEIGHTS)):
            check_protocol()
            with (ROOT/f'{index}.log').open('x') as stream:
                subprocess.run([SIM_PYTHON, str(ROOT/'calibrate.py'), '--index', str(index)],
                               stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=WORKER_TIMEOUT)
            result['rows'].append(json.loads((ROOT/'runs'/str(index)/'summary.json').read_text()))
            atomic(ROOT/'progress.json', result)
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(ROOT/'result.json', result)
        atomic(ROOT/'progress.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, choices=range(len(HEIGHTS)))
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        geometry = inspect(ROOT)
        atomic(ROOT/'geometry_check.json', geometry)
        with (ROOT/'protocol.json').open('x') as stream:
            json.dump(protocol(), stream, indent=2)
    else:
        assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
        check_protocol()
        run() if args.index is None else run_one(args.index)

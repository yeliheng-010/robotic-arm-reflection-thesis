"""独立障碍物高度扫描；只按默认执行接触确认触发，不使用模型选择条件。"""
import argparse
from contextlib import contextmanager, ExitStack
import json
import os
import subprocess
import time
from unittest.mock import patch
from stability.collection_status import atomic
from refinement.config import ROOT, COLLISION_HEIGHTS, COLLISION_CASES, SIM_PYTHON, WORKER_TIMEOUT
from refinement.freeze import verify

SAMPLE_STRIDE = 25


def observe_step(original, trace, source):
    def step(env, *args, **kwargs):
        output = original(env, *args, **kwargs)
        model, data = env.mj_model, env.mj_data
        trace['steps'] += 1
        divider = model.geom('safety_divider').id
        if 'geometry' not in trace:
            trace['geometry'] = dict(center=data.geom_xpos[divider].tolist(),
                                     halfsize=model.geom_size[divider].tolist())
        if trace['steps'] % SAMPLE_STRIDE == 0:
            trace['source_path'].append([float(data.time), *data.body(source).xpos.tolist()])
        for contact in data.contact[:data.ncon]:
            if divider not in (contact.geom1, contact.geom2):
                continue
            other = contact.geom2 if contact.geom1 == divider else contact.geom1
            name = model.body(model.geom_bodyid[other]).name
            entry = trace['divider_contacts'].setdefault(name, dict(count=0, first_time=float(data.time)))
            entry['count'] += 1
        return output
    return step


@contextmanager
def challenge(height, trace, source):
    from diversity.scene import ScenarioFault
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    original = ScenarioFault.model_editor

    def edit(fault, spec):
        original(fault, spec)
        geom = spec.geom('safety_divider')
        if height is None:
            geom.contype, geom.conaffinity = 0, 0
            geom.rgba = [0., 0., 0., 0.]
            for suffix in ('left', 'right'):
                spec.geom('safety_divider_marker_'+suffix).rgba = [0., 0., 0., 0.]
        else:
            geom.size = [geom.size[0], geom.size[1], height]
            geom.pos = [geom.pos[0], geom.pos[1], height]

    with ExitStack() as stack:
        stack.enter_context(patch.object(ScenarioFault, 'model_editor', edit))
        stack.enter_context(patch.object(UR5GraspEnv, 'step', observe_step(UR5GraspEnv.step, trace, source)))
        yield


def worker(case, index):
    from reflection.__main__ import bootstrap
    bootstrap()
    from diversity.runtime import DiverseEngine
    from controlled.config import tasks, scenario
    from refinement.audit import compare_saved
    task, height = tasks()[case], COLLISION_HEIGHTS[index]
    directory = ROOT/'collision'/f'{case:02d}_{index}'
    assert not directory.exists()
    trace = dict(steps=0, source_path=[], divider_contacts={})
    engine = DiverseEngine(scenario_config=scenario(task['seed'], 'clean'), max_attempts=1,
                           headless=True, task_parser='rule')
    try:
        with challenge(height, trace, task['source']):
            result = engine.run(source=task['source'], destination=task['destination'], seed=task['seed'],
                                fault='none', output=directory, method='retry', context='collision_calibration_v1')
    finally:
        engine.close()
    error = result['records'][0]['error'] or {}
    contacts = error.get('evidence', {}).get('contacts', [])
    triggered = error.get('error_type') == 'collision' and any('SafetyDivider' in pair for pair in contacts)
    row = dict(case=case, index=index, height=height, success=result['success'], error=error.get('error_type'),
               intended_collision=triggered, contacts=contacts, trace=trace, test_used=False)
    if height == .06:
        path = ROOT.parent/'controlled_v3/pilot/tasks'/f'{case:02d}'/'retry/result.json'
        compare_saved(result, json.loads(path.read_text()))
        row['original_default_paired'] = True
    atomic(directory/'summary.json', row)


def run():
    verify()
    root = ROOT/'collision'
    root.mkdir(exist_ok=False)
    result = dict(status='running', expected=len(COLLISION_CASES)*len(COLLISION_HEIGHTS), rows=[],
                  started_at=time.time(), job=os.environ['SLURM_JOB_ID'])
    try:
        for case in COLLISION_CASES:
            for index in range(len(COLLISION_HEIGHTS)):
                command = [SIM_PYTHON, '-m', 'refinement.collision', '--case', str(case), '--index', str(index)]
                with (root/f'{case:02d}_{index}.log').open('x') as stream:
                    subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                   check=True, timeout=WORKER_TIMEOUT)
                result['rows'].append(json.loads((root/f'{case:02d}_{index}/summary.json').read_text()))
                atomic(root/'progress.json', result)
        verify()
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(root/'result.json', result)
        atomic(root/'progress.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int)
    parser.add_argument('--index', type=int)
    args = parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    verify()
    run() if args.case is None else worker(args.case, args.index)

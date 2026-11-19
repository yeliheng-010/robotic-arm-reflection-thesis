"""独立隔离MuJoCo运动学与完整状态掩码审计；禁止积分和优化。"""
import os
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
import mujoco
from qualified_initial_state_v1 import model as helper
from qualified_projection_diagnostic_v1.common import diagnostic_only, loaded_sources, XML, PARAMETERS
from qualified_initial_projection_run_v2.protocol import (
    RUN, read, save, sha, require, verify, authorization, claim)
from qualified_initial_projection_run_v2.state import check, source_state, SIDES, PARTS


@contextmanager
def isolated_only(xml):
    compile_model, make_data = mujoco.MjModel.from_xml_string, mujoco.MjData
    allowed = dict(isolated_model=0, data=0, forward=0, rendering=0)
    models = []
    def compile_once(text):
        require(text == xml and not models, 'Unexpected model')
        model = compile_model(text)
        models.append(model)
        allowed['isolated_model'] += 1
        return model
    def data(model):
        require(models and model is models[0], 'Unexpected data model')
        allowed['data'] += 1
        return make_data(model)
    def forbidden(label):
        def call(*args, **kwargs):
            allowed[label] += 1
            raise RuntimeError('Forbidden '+label)
        return call
    with diagnostic_only() as (optimizer, motion), ExitStack() as stack:
        stack.enter_context(patch.object(mujoco.MjModel, 'from_xml_string', compile_once))
        stack.enter_context(patch.object(mujoco, 'MjData', data))
        stack.enter_context(patch.object(mujoco, 'mj_forward', forbidden('forward')))
        stack.enter_context(patch.object(mujoco, 'Renderer', forbidden('rendering')))
        yield allowed, optimizer, motion


def check_candidate(result):
    with np.load(RUN / 'candidate_state.npz', allow_pickle=False) as data:
        candidate, source = data['integration'], data['reference']
    np.testing.assert_array_equal(source_state(), source)
    parameters = read(PARAMETERS)
    values, contract = check(source, candidate, parameters)
    for side in SIDES:
        solved = result['solutions'][side]
        require(solved['accepted'] and solved['optimizer_success'] and solved['actual_optimizer_calls'] == 1,
                'Invalid solver acceptance')
        for part, angle in zip(PARTS, solved['angles']):
            require(values[f'{side}_{part}_joint'] == angle, 'Candidate differs from solver result')
    xml = helper.isolated_xml(XML)
    with (RUN / 'audit_isolated.xml').open('x', encoding='utf-8') as stream:
        stream.write(xml)
    with isolated_only(xml) as (allowed, optimizer, motion):
        model = mujoco.MjModel.from_xml_string(xml)
        helper.verify_model(model, parameters)
        layout = helper.check_state_layout(model)
        rows = helper.evaluate(model, candidate, parameters)
        require(len(rows) == len(result['connections']) == 2, 'Wrong connection count')
        for expected, actual in zip(result['connections'], rows):
            require(actual['passed'], 'Independent connection rejection')
            for frame in ('world', 'local'):
                np.testing.assert_allclose(expected[frame], actual[frame], atol=1e-12, rtol=0)
        require(not any(optimizer.values()) and not any(motion.values()), 'Forbidden audit operation')
        require(allowed['forward'] == allowed['rendering'] == 0, 'Forward/rendering invoked')
    return dict(candidate_verified=True, state_contract=contract, connections=rows, layout=layout,
        candidate_sha256=sha(RUN / 'candidate_state.npz'), allowed_counts=allowed,
        optimizer_counts=optimizer, motion_counts=motion)


def inspect():
    if (RUN / 'inventory.json').exists():
        for name, digest in read(RUN / 'inventory.json').items():
            require(sha(RUN / name) == digest, 'Construction evidence changed: '+name)
    if not (RUN / 'result.json').exists():
        with diagnostic_only() as (optimizer, motion):
            require((RUN / 'failure.json').exists(), 'Missing failure evidence')
            checked = dict(candidate_verified=False, failure_evidence_only=True,
                candidate_file_present=(RUN / 'candidate_state.npz').exists(),
                failure_sha256=sha(RUN / 'failure.json'), optimizer_counts=optimizer, motion_counts=motion)
        return checked
    result = read(RUN / 'result.json')
    if result['candidate_created']:
        return check_candidate(result)
    with diagnostic_only() as (optimizer, motion):
        require(not (RUN / 'candidate_state.npz').exists(), 'Rejected candidate was saved')
        require(any(not row['accepted'] for row in result['solutions'].values()), 'Missing rejection')
    return dict(candidate_verified=False, rejection_evidence_only=True,
                optimizer_counts=optimizer, motion_counts=motion)


def main():
    identities = verify()
    claim(authorization(), RUN, name='audit')
    try:
        checked = inspect()
        loaded = loaded_sources(identities)
        verify()
        save(RUN / 'audit_loaded_sources.json', loaded)
        save(RUN / 'audit_result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'],
            verified_identities=len(identities), full_scene_checked=False,
            production_ready=False, dynamics_validated=False, **checked))
    except Exception as error:
        save(RUN / 'audit_failure.json', dict(error=type(error).__name__+': '+str(error)))
        raise
    print(dict(passed=True, **checked), flush=True)


if __name__ == '__main__':
    main()

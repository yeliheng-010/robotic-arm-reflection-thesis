"""独立重载本轮完整MJB，复核候选的静态约束和接触。"""
import os
import numpy as np
import mujoco
from qualified_scene_candidate_v1.guard import no_motion, require_no_motion
from qualified_scene_candidate_v1.scene import candidate, restore, state
from qualified_scene_candidate_v1.checks import inspect
from qualified_scene_candidate_v1.common import (
    RUN, CANDIDATE_SHA, verify, loaded_sources, read, save, sha, require, claim)
from qualified_task_v1.integrity import fields


def compare(expected, actual):
    if isinstance(expected, dict):
        require(set(expected) == set(actual), 'Audit keys differ')
        for key in expected:
            compare(expected[key], actual[key])
    elif isinstance(expected, list):
        require(len(expected) == len(actual), 'Audit list length differs')
        for left, right in zip(expected, actual):
            compare(left, right)
    elif isinstance(expected, float):
        np.testing.assert_allclose(expected, actual, atol=1e-12, rtol=0)
    else:
        require(expected == actual, 'Audit value differs')


def evaluate():
    for name, digest in read(RUN / 'inventory.json').items():
        require(sha(RUN / name) == digest, 'Scene evidence changed: '+name)
    metadata, result = read(RUN / 'model.json'), read(RUN / 'result.json')
    require(sha(RUN / 'model.mjb') == metadata['model_sha256'], 'Model changed')
    model = mujoco.MjModel.from_binary_path(str(RUN / 'model.mjb'))
    require(fields(model) == metadata['model_fields'], 'Reloaded model fields differ')
    data = mujoco.MjData(model)
    restore(model, data, candidate())
    checked = inspect(model, data, source=metadata['source'])
    compare(read(RUN / 'static.json'), checked)
    np.testing.assert_array_equal(candidate(), state(model, data))
    with np.load(RUN / 'observation/source_state.npz', allow_pickle=False) as original:
        np.testing.assert_array_equal(candidate(), original['state'])
    qualified = read(RUN / 'observation/qualification.json')
    require(qualified['accepted'] == result['observation']['qualified'], 'Qualification flag differs')
    require(read(RUN / 'observation/isolation.json')['passed'], 'Observation isolation failed')
    return dict(static_geometry_passed=checked['passed'], observation_qualified=qualified['accepted'],
        model_sha256=metadata['model_sha256'], model_fields_reloaded_identically=True,
        candidate_state_unchanged=True, fresh_rendering_performed=False)


def main():
    identities = verify()
    require(read(RUN / 'scene_claim.json')['consumed'] == 1, 'Missing scene claim')
    claim(RUN, 'audit')
    with no_motion() as counts:
        try:
            checked = evaluate()
            loaded = loaded_sources(identities)
            require_no_motion(counts)
            require(counts['binary_load'] == 1 and counts['reset'] == counts['spec_compile'] == 0, 'Audit history')
            verify()
            save(RUN / 'audit_loaded_sources.json', loaded)
            save(RUN / 'audit_result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'],
                counts=counts, verified_identities=len(identities), candidate_sha256=CANDIDATE_SHA,
                production_ready=False, dynamics_validated=False, **checked))
        except Exception as error:
            save(RUN / 'audit_failure.json', dict(error=type(error).__name__+': '+str(error), counts=counts))
            raise
    print(dict(passed=True, counts=counts, **checked), flush=True)


if __name__ == '__main__':
    main()

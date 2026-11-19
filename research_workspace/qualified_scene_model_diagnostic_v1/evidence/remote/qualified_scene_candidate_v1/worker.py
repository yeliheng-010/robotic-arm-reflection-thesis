"""完整场景单候选静态检查与一次固定相机资格采集。"""
import os
import numpy as np
import mujoco
from qualified_scene_candidate_v1.guard import no_motion, require_no_motion
from qualified_scene_candidate_v1.scene import restored_scene, state, candidate
from qualified_scene_candidate_v1.checks import inspect
from qualified_scene_candidate_v1.common import (
    ROOT, PROJECT, RUN, CANDIDATE_SHA, verify, loaded_sources, read, save, sha, require, claim)
from qualified_task_v1.observer import observe, ObservationRejected
from qualified_task_v1.integrity import fields, fingerprint, unchanged


def capture(env, config):
    try:
        observe(env, config, folder=RUN / 'observation')
        return dict(qualified=True, reason=None)
    except ObservationRejected as error:
        return dict(qualified=False, reason=str(error))


def execute(counts):
    case = read(PROJECT / 'qualified_task_v1/run/manifest.json')['cases']['978505']
    save(RUN / 'case.json', case)
    with restored_scene(case['config']) as (env, layout):
        before = fingerprint(env)
        checked = inspect(env.mj_model, env.mj_data, source=case['item']['source'])
        save(RUN / 'static.json', checked)
        path = RUN / 'model.mjb'
        require(not path.exists(), 'Model snapshot exists')
        mujoco.mj_saveModel(env.mj_model, str(path))
        save(RUN / 'model.json', dict(layout=layout, model_fields=fields(env.mj_model),
            model_sha256=sha(path), mujoco_version=mujoco.__version__, candidate_sha256=CANDIDATE_SHA,
            source=case['item']['source'], reconstructed_without_settle=True,
            historical_binary_equality_proven=False))
        observation = capture(env, case['config'])
        isolation = unchanged(before, fingerprint(env))
        np.testing.assert_array_equal(candidate(), state(env.mj_model, env.mj_data))
    require_no_motion(counts)
    require(counts['reset'] == counts['spec_compile'] == 1 and counts['binary_load'] == 0,
            'Unexpected construction history')
    return dict(static_geometry_passed=checked['passed'], observation=observation, isolation=isolation,
        all_checks_passed=bool(checked['passed'] and observation['qualified']),
        full_scene_checked=True, production_ready=False, dynamics_validated=False)


def main():
    identities = verify()
    prepared = read(ROOT / 'prepared.json')
    require(prepared['passed'] and prepared['bindings_sha256'] == sha(ROOT / 'BINDINGS.json'), 'Not prepared')
    claim(RUN, 'scene')
    with no_motion() as counts:
        try:
            result = execute(counts)
            loaded = loaded_sources(identities)
            verify()
            save(RUN / 'loaded_sources.json', loaded)
            save(RUN / 'result.json', dict(job=os.environ['SLURM_JOB_ID'], counts=counts,
                verified_identities=len(identities), candidate_sha256=CANDIDATE_SHA, **result))
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__+': '+str(error), counts=counts))
            raise
    save(RUN / 'inventory.json', {str(p.relative_to(RUN)): sha(p) for p in RUN.rglob('*') if p.is_file()})
    print(dict(**result, counts=counts), flush=True)


if __name__ == '__main__':
    main()

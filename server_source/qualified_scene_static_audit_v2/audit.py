"""固定MJB/候选的独立静态复算，不重建场景、不积分或渲染。"""
import os
import unittest
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import numpy as np
import mujoco
from qualified_scene_model_diagnostic_v1.diagnose import verify as verify_parent
from qualified_scene_candidate_v1.guard import no_motion, require_no_motion, blocked
from qualified_scene_candidate_v1.common import (
    PROJECT, RUN as SOURCE, read, save, sha, require, loaded_sources, claim)
from qualified_scene_candidate_v1.scene import candidate, restore, state
from qualified_scene_candidate_v1.checks import inspect
from qualified_scene_candidate_v1.audit import compare
from qualified_task_v1.integrity import fields
from qualified_scene_static_audit_v2.gate import serialized_identity
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'
PACKAGE = PROJECT / 'env_sim/lib/python3.11/site-packages/mujoco/include/mujoco'


def verify():
    identities, records = verify_parent()
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        require(sha(PROJECT / name) == digest, 'Changed static audit input: '+name)
        identities[str(PROJECT / name)] = digest
    require(mujoco.__version__ == '3.3.7', 'Unexpected MuJoCo version')
    for name in ('mjmodel.h', 'mjxmacro.h'):
        require(sha(PACKAGE / name) == sha(ROOT / 'reference' / name), 'Official header mismatch')
    return identities, records


def static_audit():
    metadata = read(SOURCE / 'model.json')
    require(sha(SOURCE / 'model.mjb') == metadata['model_sha256'], 'MJB changed')
    model = mujoco.MjModel.from_binary_path(str(SOURCE / 'model.mjb'))
    before = fields(model)
    identity = serialized_identity(metadata['model_fields'], before)
    data = mujoco.MjData(model)
    values = candidate()
    restore(model, data, values)
    checked = inspect(model, data, source=metadata['source'])
    compare(read(SOURCE / 'static.json'), checked)
    np.testing.assert_array_equal(values, state(model, data))
    with np.load(SOURCE / 'observation/source_state.npz', allow_pickle=False) as saved:
        np.testing.assert_array_equal(values, saved['state'])
    require(before == fields(model), 'Static inspection changed model')
    save(RUN / 'static.json', checked)
    save(RUN / 'model_fields.json', before)
    return dict(identity=identity, static_geometry_passed=checked['passed'],
        state_unchanged=True, integration_state_size=values.size,
        model_sha256=sha(SOURCE / 'model.mjb'), model_size=(SOURCE / 'model.mjb').stat().st_size,
        static_comparison_atol=1e-12, physical_thresholds_unchanged=True)


def execute(counts):
    counts.update(forward=0, rendering=0)
    original_forward = mujoco.mj_forward
    def forward(*args, **kwargs):
        counts['forward'] += 1
        require(counts['forward'] == 1, 'Only one forward allowed')
        return original_forward(*args, **kwargs)
    with ExitStack() as stack:
        for owner, name, label in ((UR5GraspEnv, 'reset', 'reset'),
                                   (mujoco.MjSpec, 'compile', 'spec_compile'),
                                   (mujoco.Renderer, 'render', 'rendering')):
            stack.enter_context(patch.object(owner, name, blocked(counts, label)))
        stack.enter_context(patch.object(mujoco, 'mj_forward', forward))
        tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
            'qualified_scene_static_audit_v2.test_gate'))
        require(tests.wasSuccessful(), 'Identity gate tests failed')
        checked = static_audit()
    require_no_motion(counts)
    require(counts['binary_load'] == counts['forward'] == 1, 'Unexpected load/forward count')
    require(all(counts[k] == 0 for k in ('reset', 'spec_compile', 'rendering')), 'Unexpected construction')
    return checked, tests.testsRun


def main():
    identities, records = verify()
    claim(RUN, 'static')
    with no_motion() as counts:
        try:
            checked, tests = execute(counts)
            loaded = loaded_sources(identities)
            verify()
            save(RUN / 'loaded_sources.json', loaded)
            save(RUN / 'result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'], tests=tests,
                counts=counts, verified_identities=len(identities), record_verification=records,
                original_failures_preserved=True, observation_qualified=False,
                production_ready=False, dynamics_validated=False, **checked))
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__+': '+str(error), counts=counts))
            raise
    save(RUN / 'inventory.json', {p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    print(dict(passed=True, tests=tests, counts=counts, **checked), flush=True)


if __name__ == '__main__':
    main()

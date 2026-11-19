"""只读重载6878模型并列出字段差异，复核已保存RGB。"""
import os
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import numpy as np
import mujoco
from qualified_scene_candidate_audit_v1 import audit as prior
from qualified_scene_candidate_v1.guard import no_motion, require_no_motion, blocked
from qualified_scene_candidate_v1.common import (
    PROJECT, RUN as SOURCE, read, save, sha, require, loaded_sources, claim)
from qualified_task_v1.integrity import fields
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'


def verify():
    identities, records = prior.verify()
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        require(sha(PROJECT / name) == digest, 'Changed diagnostic input: '+name)
        identities[str(PROJECT / name)] = digest
    require(not (prior.RUN / 'result.json').exists(), '6879 failure rewritten')
    require(read(prior.RUN / 'failure.json')['error'] ==
            'ValueError: Reloaded model fields differ', 'Unexpected audit failure')
    return identities, records


def detail(model, key):
    value = model
    for part in key.split('.'):
        value = getattr(value, part)
    if isinstance(value, np.ndarray):
        return dict(type='ndarray', shape=list(value.shape), dtype=str(value.dtype),
                    values=value.tolist() if value.size <= 32 else None)
    return dict(type=type(value).__name__, value=repr(value))


def model_difference():
    metadata = read(SOURCE / 'model.json')
    path = SOURCE / 'model.mjb'
    require(sha(path) == metadata['model_sha256'], 'MJB changed')
    model = mujoco.MjModel.from_binary_path(str(path))
    before, after = metadata['model_fields'], fields(model)
    changed = [dict(field=k, saved=before.get(k), reloaded=after.get(k),
                    reloaded_detail=detail(model, k) if k in after else None)
               for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)]
    result = dict(saved_fields=len(before), reloaded_fields=len(after),
                  exact_match=before == after, differences=changed,
                  model_sha256=sha(path), model_size=path.stat().st_size,
                  mujoco_version=mujoco.__version__, reloaded_fingerprints=after)
    save(RUN / 'model_difference.json', result)
    return dict(exact_match=result['exact_match'], differences=changed,
                model_sha256=result['model_sha256'], model_size=result['model_size'])


def execute(counts):
    counts.update(forward=0, rendering=0)
    with ExitStack() as stack:
        for owner, name, label in ((UR5GraspEnv, 'reset', 'reset'),
                                   (mujoco.MjSpec, 'compile', 'spec_compile'),
                                   (mujoco, 'mj_forward', 'forward'),
                                   (mujoco.Renderer, 'render', 'rendering')):
            stack.enter_context(patch.object(owner, name, blocked(counts, label)))
        model = model_difference()
        with patch.object(prior, 'RUN', RUN):
            observation = prior.observation_audit()
    require_no_motion(counts)
    require(counts['binary_load'] == 1, 'Expected one binary read')
    require(all(counts[k] == 0 for k in ('reset', 'spec_compile', 'forward', 'rendering')),
            'Unexpected simulator action')
    return dict(model=model, observation=observation)


def main():
    identities, records = verify()
    claim(RUN, 'diagnostic')
    with no_motion() as counts:
        try:
            checked = execute(counts)
            loaded = loaded_sources(identities)
            verify()
            save(RUN / 'loaded_sources.json', loaded)
            save(RUN / 'result.json', dict(diagnostic_completed=True, job=os.environ['SLURM_JOB_ID'],
                counts=counts, verified_identities=len(identities), record_verification=records,
                original_failures_preserved=True, static_geometry_recomputed=False,
                production_ready=False, dynamics_validated=False, **checked))
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__+': '+str(error), counts=counts))
            raise
    save(RUN / 'inventory.json', {p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    print(dict(diagnostic_completed=True, **checked, counts=counts), flush=True)


if __name__ == '__main__':
    main()

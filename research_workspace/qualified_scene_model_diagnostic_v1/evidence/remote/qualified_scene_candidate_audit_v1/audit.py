"""只复核6878已保存证据；不重建场景或渲染。"""
import os
import csv
import base64
from pathlib import Path
import numpy as np
import mujoco
import cv2
from qualified_scene_candidate_v1.guard import no_motion, require_no_motion
from qualified_scene_candidate_v1.common import (
    PROJECT, RUN as SOURCE, CANDIDATE_SHA, read, save, sha, require, verify as verify_parent, loaded_sources, claim)
from qualified_scene_candidate_v1.scene import candidate, restore, state
from qualified_scene_candidate_v1.checks import inspect
from qualified_scene_candidate_v1.audit import compare
from qualified_task_v1.integrity import fields
from observation_search_v1 import stable
from sensor_independent_v2.rgb_policy import assess
from cv_policy import frame_gate

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'
PACKAGE = PROJECT / 'env_sim/lib/python3.11/site-packages'
RECORD = PACKAGE / 'pyopengl-3.1.10.dist-info/RECORD'
NAMES = ('ctypesarrays', 'ctypesparameters', 'ctypespointers', 'lists', 'nones')


def verify():
    identities = dict(verify_parent())
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        require(sha(PROJECT / name) == digest, 'Changed evidence: '+name)
        identities[str(PROJECT / name)] = digest
    require(sha(RECORD) == identities[str(RECORD)], 'Frozen installation RECORD changed')
    with RECORD.open(newline='', encoding='utf-8') as stream:
        records = {row[0]: row for row in csv.reader(stream)}
    checked = []
    for name in NAMES:
        relative = 'OpenGL/arrays/'+name+'.py'
        path = PACKAGE / relative
        digest = sha(path)
        encoded = base64.urlsafe_b64encode(bytes.fromhex(digest)).decode().rstrip('=')
        require(records[relative][1] == 'sha256='+encoded, 'Installed file does not match RECORD')
        require(int(records[relative][2]) == path.stat().st_size, 'Installed size differs')
        checked.append(dict(path=str(path), sha256=digest, record_matched=True))
    failure = read(SOURCE / 'failure.json')
    require('Unbound imported files' in failure['error'], 'Unexpected original failure')
    require(not (SOURCE / 'result.json').exists(), 'Original failure rewritten')
    return identities, checked


def static_audit():
    metadata = read(SOURCE / 'model.json')
    require(sha(SOURCE / 'model.mjb') == metadata['model_sha256'], 'MJB changed')
    model = mujoco.MjModel.from_binary_path(str(SOURCE / 'model.mjb'))
    require(fields(model) == metadata['model_fields'], 'Reloaded model fields differ')
    data = mujoco.MjData(model)
    restore(model, data, candidate())
    checked = inspect(model, data, source=metadata['source'])
    compare(read(SOURCE / 'static.json'), checked)
    np.testing.assert_array_equal(candidate(), state(model, data))
    with np.load(SOURCE / 'observation/source_state.npz', allow_pickle=False) as saved:
        np.testing.assert_array_equal(candidate(), saved['state'])
    return dict(static_geometry_passed=checked['passed'], model_fields_matched=len(metadata['model_fields']),
        integration_state_size=candidate().size, candidate_state_unchanged=True,
        model_sha256=metadata['model_sha256'], static_checks=checked)


def observation_audit():
    folder = SOURCE / 'observation'
    report = read(folder / 'qualification.json')
    require(read(folder / 'isolation.json')['passed'], 'Observation isolation failed')
    with np.load(folder / 'rgb_0.npz', allow_pickle=False) as data:
        frames = stable.decode(data)
    last_stable = stable.check_record(frames[:-1], report['rgb']['stability'])
    require(assess(last_stable, frames[-1]) == report['rgb']['post'], 'RGB post check differs')
    require(assess(frames[0], frames[-1]) == report['rgb']['initial'], 'RGB initial check differs')
    require(frame_gate(report['measurements']) == report['gate'], 'Saved measurement gate differs')
    accepted = bool(report['gate']['passed'] and report['calibration']['passed'] and report['rgb']['eligible'])
    require(accepted == report['accepted'], 'Observation acceptance differs')
    path = RUN / 'saved_observation.png'
    require(not path.exists(), 'Preview already exists')
    require(cv2.imwrite(str(path), cv2.cvtColor(frames[-1], cv2.COLOR_RGB2BGR)), 'Preview write failed')
    return dict(observation_qualified=accepted, rejected=report['gate']['rejected'],
        recorded_calibration_passed=report['calibration']['passed'], calibration_recomputed=False,
        segmentation_measurements_recomputed=False, saved_measurement_policy_verified=True,
        rgb_pixels_verified=True, pixel_sha256=report['rgb']['post']['after_sha256'],
        png_sha256=sha(path), fresh_rendering_performed=False)


def main():
    identities, records = verify()
    claim(RUN, 'audit')
    with no_motion() as counts:
        try:
            static = static_audit()
            observation = observation_audit()
            loaded = loaded_sources(identities)
            require_no_motion(counts)
            require(counts['binary_load'] == 1 and counts['reset'] == counts['spec_compile'] == 0, 'Audit history')
            verify()
            save(RUN / 'loaded_sources.json', loaded)
            save(RUN / 'result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'], counts=counts,
                verified_identities=len(identities), record_verification=records, static=static,
                observation=observation, original_failure_preserved=True, production_ready=False,
                all_checks_passed=bool(static['static_geometry_passed'] and observation['observation_qualified']),
                candidate_sha256=CANDIDATE_SHA, dynamics_validated=False))
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__+': '+str(error), counts=counts))
            raise
    save(RUN / 'inventory.json', {p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    print(dict(passed=True, static_geometry_passed=static['static_geometry_passed'],
               observation=observation, counts=counts), flush=True)


if __name__ == '__main__':
    main()

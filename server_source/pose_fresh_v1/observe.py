"""先资格后诊断；静置之后禁止积分，任何视角均不授权执行。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import mujoco
import numpy as np
import cv_select
from cv_policy import REQUIRED
from sd_inventory import root_boxes
from sf_camera import framed, proposal
from live_observations import state
from coverage_repair_v1.proposals import changed
from visibility_calibration_v1 import capture
from pose_fresh_v1.policy import CAMERA_BUDGET, OFFSETS, NOISE_PREFIX
from pose_fresh_v1.common import save


def forbid(*args, **kwargs):
    raise RuntimeError('Integration forbidden after initialization')


@contextmanager
def paused(env, folder):
    before = state(env).copy()
    with (folder / 'initial_state.npz').open('xb') as stream:
        np.savez_compressed(stream, state=before)
    with ExitStack() as stack:
        stack.enter_context(patch.object(env, 'step', forbid))
        for name in ('mj_step', 'mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, forbid))
        yield
        after = state(env).copy()
        np.testing.assert_array_equal(before, after)
        with (folder / 'final_state.npz').open('xb') as stream:
            np.savez_compressed(stream, state=after)
    save(folder / 'state_check.json', dict(integration_state_unchanged=True,
        initialization_steps=cv_select.SETTLE_STEPS, task_motion_steps=0,
        integration_calls_forbidden=True, isolated_environment=True))


def search(env, renderer, *, config, boxes, folder):
    attempts = []
    for index in range(CAMERA_BUDGET):
        camera = config['camera'] if index == 0 else proposal(config['seed'], index, boxes=boxes)
        frame = framed(boxes, camera)
        report = (cv_select.evaluate(env, renderer, camera, boxes=boxes) if frame['passed']
                  else dict(accepted=False, reason='framing_rejected', framing=frame))
        attempts.append(dict(index=index, camera=camera, **report))
        if report['accepted']:
            break
    save(folder / 'selection.json', dict(attempts=attempts, accepted=attempts[-1]['accepted']))
    return attempts[-1]['camera'] if attempts[-1]['accepted'] else None


def slots(env, renderer, *, anchor, boxes, config, folder):
    bounds = np.asarray(list(boxes.values()))
    center = (bounds[:, 0].min(axis=0) + bounds[:, 1].max(axis=0)) / 2
    snapshot = dict(case=dict(item=dict(seed=config['seed'], source='PurpleCapsule'), config=config))
    rows, clouds = [], {}
    for index, (azimuth, elevation) in enumerate(OFFSETS):
        camera = anchor if index == 0 else changed(anchor, np.array([azimuth, elevation, 0, 0, 0, 0]), center)
        if camera is None:
            rows.append(dict(index=index, calibration_passed=False,
                full_frame_qualified=False, reason='camera_bounds_rejected'))
            continue
        row, data = capture.view(env, renderer, camera=camera, boxes=boxes,
            snapshot=snapshot, phase_id=0, index=index, folder=folder / f'view_{index}')
        row['full_frame_qualified'] = bool(row['calibration_passed'] and row['report'].get('gate', {}).get('passed'))
        row.update(training_eligible=False, control_eligible=False)
        rows.append(row)
        if data is not None:
            clouds[index] = data
    assert rows[0]['full_frame_qualified'], 'Approved anchor failed repeated qualification'
    save(folder / 'views.json', rows)
    return rows, clouds


def run(config, folder):
    with cv_select.scene(config) as (env, renderer), paused(env, folder):
        all_boxes = root_boxes(env.mj_model, env.mj_data)
        boxes = {name: all_boxes[name] for name in REQUIRED}
        anchor = search(env, renderer, config=config, boxes=boxes, folder=folder)
        if anchor is None:
            return None
        geom = env.mj_model.geom('purple_capsule').id
        assert int(env.mj_model.geom_type[geom]) == int(mujoco.mjtGeom.mjGEOM_CAPSULE)
        save(folder / 'private_truth.json', dict(center=env.mj_data.geom_xpos[geom].tolist(),
            axis=env.mj_data.geom_xmat[geom].reshape(3, 3)[:, 2].tolist(), private_simulation_truth=True))
        with patch.object(capture, 'SEED_PREFIX', NOISE_PREFIX):
            return slots(env, renderer, anchor=anchor, boxes=boxes, config=config, folder=folder)

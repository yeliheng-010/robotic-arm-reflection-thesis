"""分别复核保存原缓存和重建缓存，额外派生诊断亦逐项校验。"""
import numpy as np
from qualified_closure_mjb_v1.protocol import proposal, read, require, commands
from qualified_closure_dynamics_v1.capture import pack, restore, state, unpack, collisions
from qualified_closure_dynamics_v1.backend import reference_vectors
from qualified_scene_candidate_v1.checks import inspect


def diagnostics(model, values, metadata):
    ids = [model.joint(f'{s}_{p}_joint').id for s in ('right', 'left')
           for p in ('driver', 'coupler', 'spring_link', 'follower')]
    angles = values['cached_qpos'][model.jnt_qposadr[ids]]
    body = model.body('2f85_base').id
    tcp = values['cached_xpos'][body] + values['cached_xmat'][body].reshape(3, 3) @ np.asarray(
        proposal()['tcp_local_translation_m'])
    return dict(finger_angles=angles, finger_velocities=values['cached_qvel'][model.jnt_dofadr[ids]],
        reference_distances=np.max(np.abs(reference_vectors(metadata['inputs'])-angles), axis=1),
        spring_asymmetry=np.asarray(angles[2]-angles[6]),
        arm_drift=values['cached_qpos'][model.jnt_qposadr[:6]]-metadata['inputs']['command'],
        tcp_drift=tcp-metadata['initial_tcp'])


def check_state(model, values, *, row, metadata):
    for label in ('cached', 'rebuilt'):
        cache = {k[len(label)+1:]: values[k] for k in values if k.startswith(label+'_')}
        require(collisions(model, unpack(cache), metadata['source']) == row[label+'_hits'],
                'Saved cache classification differs')
    data = restore(model, values['integration'])
    np.testing.assert_array_equal(values['integration'], state(model, data))
    for key, value in pack(data).items():
        np.testing.assert_array_equal(values['rebuilt_'+key], value, err_msg=key)
    for key, value in diagnostics(model, values, metadata).items():
        np.testing.assert_array_equal(values[key], value, err_msg=key)
    nonfinite = not all(np.isfinite(values[k]).all() for k in values
                       if k == 'integration' or k.startswith(('cached_', 'rebuilt_')))
    warnings = bool(np.any(values['cached_warning_number']) or np.any(values['rebuilt_warning_number']))
    require(row['nonfinite'] == nonfinite and row['warnings'] == warnings, 'Numeric flags differ')
    require(row['model_changed'] is False, 'Model changed in original observation')
    return data


def audit_states(folder, model, *, metadata, count):
    minimum = np.full(5, np.inf)
    for index in range(count+1):
        row = read(folder/f'observed_{index:04d}.json')
        with np.load(folder/f'state_{index:04d}.npz', allow_pickle=False) as values:
            data = check_state(model, values, row=row, metadata=metadata)
            expected = np.r_[metadata['inputs']['command'], commands()[index-1] if index else 0.0]
            np.testing.assert_array_equal(expected, values['cached_ctrl'])
            require(row['simulation_time'] == float(values['cached_time']), 'Stored time differs')
            require(abs(row['simulation_time']-metadata['initial_time']-index*metadata['timestep']) <= 1e-9,
                    'Simulation time/steps differ')
            require(row['initial_rejections'] == (metadata['initial_rejections'] if index == 0 else []),
                    'Initial rejection differs')
            if index == 0:
                from qualified_scene_candidate_v1.scene import candidate
                np.testing.assert_array_equal(candidate(), values['integration'])
                checked = inspect(model, data, source=metadata['source'])
                require(checked['passed'] == (not metadata['initial_rejections']), 'Initial static gate differs')
            minimum = np.minimum(minimum, values['reference_distances'])
    return minimum.tolist()

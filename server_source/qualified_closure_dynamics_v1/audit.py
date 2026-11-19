"""只读双时点复核：加载MJB和保存状态，禁止环境工厂及积分。"""
import os
from qualified_closure_dynamics_v1.protocol import ROOT, RUN, read, save, sha, require, commands


def trace_contract(folder):
    from qualified_closure_dynamics_v1.worker import reasons
    result = read(folder / 'result.json')
    count = result['completed_steps']
    require(result['uncertain_step'] is None and result['error'] is None, 'Incomplete trajectory')
    require(result['task_step_requests'] == count <= 1000, 'Step count mismatch')
    require(result['setup_steps'] == 500, 'Setup count mismatch')
    require(len(list(folder.glob('state_*.npz'))) == count + 1, 'Missing or extra state')
    require(len(list(folder.glob('observed_*.json'))) == count + 1, 'Missing or extra observation')
    require(len(list(folder.glob('intent_*.json'))) == count, 'Unconfirmed intent')
    controls = commands()
    for index in range(count + 1):
        row = read(folder / f'observed_{index:04d}.json')
        require(row['step'] == row['task_steps'] == index, 'Trace sequence mismatch')
        if index < count:
            require(not reasons(row), 'Integrated after stop condition')
        if index:
            intent = read(folder / f'intent_{index:04d}.json')
            require(intent == dict(step=index, gripper_command=controls[index - 1]), 'Command mismatch')
    expected = reasons(row) or (['budget_exhausted'] if count == 1000 else ['wall_timeout'])
    require(result['reasons'] == expected, 'Stop reason mismatch')
    return count


def audit_states(folder, model, *, metadata, count):
    import numpy as np
    from qualified_closure_dynamics_v1.capture import pack, restore, unpack, collisions
    from qualified_closure_dynamics_v1.backend import reference_vectors
    joints = [model.joint(f'{s}_{p}_joint').id for s in ('right', 'left')
              for p in ('driver', 'coupler', 'spring_link', 'follower')]
    minimum = np.full(5, np.inf)
    for index in range(count + 1):
        row = read(folder / f'observed_{index:04d}.json')
        with np.load(folder / f'state_{index:04d}.npz', allow_pickle=False) as values:
            for label in ('cached', 'rebuilt'):
                cached = {key[len(label) + 1:]: values[key] for key in values if key.startswith(label + '_')}
                require(collisions(model, unpack(cached), metadata['source']) == row[label + '_hits'],
                        'Saved cache classification mismatch')
            rebuilt = pack(restore(model, values['integration']))
            for key, value in rebuilt.items():
                np.testing.assert_array_equal(values['rebuilt_' + key], value, err_msg=key)
            require(abs(row['simulation_time'] - metadata['initial_time'] - index * metadata['timestep'])
                    <= 1e-9, 'Trace simulation time mismatch')
            expected = np.r_[metadata['inputs']['command'], commands()[index - 1] if index else 0.0]
            np.testing.assert_array_equal(expected, values['cached_ctrl'])
            angles = values['cached_qpos'][model.jnt_qposadr[joints]]
            np.testing.assert_array_equal(angles, values['finger_angles'])
            distances = np.max(np.abs(reference_vectors(metadata['inputs']) - angles), axis=1)
            np.testing.assert_array_equal(distances, values['reference_distances'])
            minimum = np.minimum(minimum, distances)
    return minimum.tolist()


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require((RUN / 'result.json').is_file(), 'No completed diagnostic evidence')
    for name, digest in read(RUN / 'primary_inventory.json').items():
        require(sha(RUN / name) == digest, 'Primary evidence changed: ' + name)
    save(RUN / 'audit_claim.json', dict(consumed=1, job=os.environ['SLURM_JOB_ID']))
    from reflection.__main__ import bootstrap
    bootstrap()
    import mujoco
    from unittest.mock import patch
    from qualified_execution_v1 import environment
    from qualified_closure_dynamics_v1.limits import guarded, forbid
    from qualified_task_v1.integrity import fields
    metadata = read(RUN / 'metadata.json')
    require(metadata['mujoco_version'] == mujoco.__version__, 'MuJoCo version mismatch')
    require(metadata['model_sha256'] == sha(RUN / 'model.mjb'), 'Model changed')
    with guarded(mujoco), patch.object(environment, 'scene', forbid):
        model = mujoco.MjModel.from_binary_path(str(RUN / 'model.mjb'))
        require(fields(model) == metadata['model_fields'], 'Compiled model differs')
        count = trace_contract(RUN)
        minimum = audit_states(RUN, model, metadata=metadata, count=count)
    identities = {p.name: sha(p) for p in RUN.iterdir() if p.is_file()}
    save(RUN / 'audit_result.json', dict(passed=True, task_steps=count,
         minimum_reference_distance_rad=minimum, integration_steps=0, identities=identities,
         cross_timing_equality_required=False, production_ready=False))


if __name__ == '__main__':
    main()

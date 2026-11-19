"""完整积分状态与两时点缓存；只forward私有副本。"""
import os
from types import SimpleNamespace
import mujoco
import numpy as np
from qualified_closure_dynamics_v1.protocol import save, require
from qualified_closure_v1.geometry import collisions

ARRAYS = ('qpos', 'qvel', 'qacc', 'ctrl', 'xpos', 'xmat', 'geom_xpos', 'geom_xmat',
          'actuator_force', 'qfrc_passive', 'qfrc_actuator', 'actuator_length',
          'actuator_velocity', 'efc_type', 'efc_id', 'efc_pos', 'eq_active')


def state(model, data):
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    result = np.empty(mujoco.mj_stateSize(model, spec))
    mujoco.mj_getState(model, data, result, spec)
    return result


def restore(model, values):
    data = mujoco.MjData(model)
    mujoco.mj_setState(model, data, values, mujoco.mjtState.mjSTATE_INTEGRATION)
    mujoco.mj_forward(model, data)
    return data


def pack(data):
    result = {name: getattr(data, name).copy() for name in ARRAYS}
    contacts = data.contact[:data.ncon]
    result.update(time=np.asarray(data.time),
        warning_number=np.asarray(data.warning.number).copy(),
        contact_geom=np.asarray([[c.geom1, c.geom2] for c in contacts], dtype=int).reshape(-1, 2),
        contact_distance=np.asarray([c.dist for c in contacts]),
        contact_position=np.asarray([c.pos.copy() for c in contacts]).reshape(-1, 3),
        contact_frame=np.asarray([c.frame.copy() for c in contacts]).reshape(-1, 9))
    return result


def unpack(values):
    contacts = [SimpleNamespace(geom1=int(g[0]), geom2=int(g[1]), dist=float(d), pos=p)
                for g, d, p in zip(values['contact_geom'], values['contact_distance'],
                                   values['contact_position'])]
    return SimpleNamespace(contact=contacts, ncon=len(contacts))


def write_npz(path, values):
    with path.open('xb') as stream:
        np.savez_compressed(stream, **values)
        stream.flush()
        os.fsync(stream.fileno())


def observe(model, live, *, source):
    before = state(model, live)
    cached = pack(live)
    rebuilt_data = restore(model, before)
    rebuilt = pack(rebuilt_data)
    np.testing.assert_array_equal(before, state(model, live))
    after = pack(live)
    require(all(np.array_equal(value, after[name], equal_nan=True)
                for name, value in cached.items()), 'Capture mutated live caches')
    row = dict(cached_hits=collisions(model, unpack(cached), source),
               rebuilt_hits=collisions(model, unpack(rebuilt), source),
               nonfinite=not all(np.isfinite(v).all() for v in
                                [before, *cached.values(), *rebuilt.values()]),
               warnings=bool(np.any(cached['warning_number']) or
                             np.any(rebuilt['warning_number'])), model_changed=False)
    return row, dict(integration=before, **{'cached_' + k: v for k, v in cached.items()},
                     **{'rebuilt_' + k: v for k, v in rebuilt.items()})


class Sink:
    def __init__(self, folder, backend):
        self.folder, self.backend = folder, backend

    def intent(self, index, command):
        save(self.folder / f'intent_{index:04d}.json', dict(step=index, gripper_command=command))

    def observed(self, index, row):
        write_npz(self.folder / f'state_{index:04d}.npz', self.backend.pending_arrays)
        save(self.folder / f'observed_{index:04d}.json', dict(step=index, **row))

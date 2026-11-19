"""只恢复候选，不再次放置、清零或求解。"""
from types import SimpleNamespace
import numpy as np
import mujoco
from qualified_closure_mjb_v1.protocol import PROJECT, proposal, read, sha, require, save
from qualified_task_v1.integrity import fields
from qualified_scene_candidate_v1.scene import ARMS, candidate, restore, state, layout
from qualified_scene_candidate_v1.checks import inspect
from qualified_closure_dynamics_v1.capture import write_npz


def model_identity(model):
    plan = proposal()
    expected = read(PROJECT/plan['model']['reloaded_fields'])
    actual = fields(model)
    require(actual == expected and len(actual) == 626, 'Reloaded model identity mismatch')
    require(mujoco.__version__ == plan['model']['mujoco_version'], 'MuJoCo version changed')
    return actual


def load_model(resources):
    plan = proposal()
    path = PROJECT/plan['model']['path']
    require(sha(path) == plan['model']['sha256'] and path.stat().st_size == plan['model']['size'], 'MJB changed')
    resources.allow_load = True
    model = mujoco.MjModel.from_binary_path(str(path))
    resources.allow_load = False
    model_identity(model)
    return model


def prepare(resources, folder):
    plan = proposal()
    require(sha(PROJECT/plan['candidate']['path']) == plan['candidate']['sha256'], 'Candidate changed')
    model = load_model(resources)
    data = mujoco.MjData(model)
    resources.gate.bind(model, data)
    values = candidate()
    restore(model, data, values)
    mapping = layout(SimpleNamespace(mj_model=model, mj_data=data, joint_names=ARMS))
    np.testing.assert_array_equal(np.r_[plan['arm_command'], 0.0], data.ctrl)
    for name in ('qvel', 'qacc_warmstart', 'qfrc_applied', 'xfrc_applied'):
        require(not np.any(getattr(data, name)), 'Frozen zero field differs: '+name)
    np.testing.assert_array_equal(values, state(model, data))
    checked = inspect(model, data, source=plan['source'])
    write_npz(folder/'restored_state.npz', dict(integration=values))
    save(folder/'initial.json', dict(kind='fixed_projected_synthetic_candidate', layout=mapping,
         candidate_sha256=plan['candidate']['sha256'], state_unchanged=True, static=checked))
    model_identity(model)
    return model, data, [] if checked['passed'] else ['initial_constraints']
